"""ServiceContainer — owns all service instances and orchestrates initialisation.

Services are created lazily on the first API request via ``container.initialise()``.
The container is stored on ``app.container`` by the app factory and accessed from
blueprints via ``current_app.container``.

Wave initialisation (parallel where dependencies allow):

  Wave 1 (parallel): WeatherService, TrainerRoadService, RouteLibraryService
  Wave 2 (serial):   AnalysisService(weather_service=...)
  Wave 3 (parallel): CommuteService, PlannerService
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.jobs.job_state import JobRegistry

logger = logging.getLogger(__name__)


class ServiceContainer:
    """Holds all application service singletons.

    Attributes mirror the module-level globals in launch.py so that
    blueprints can access them via ``current_app.container.<name>``.
    """

    def __init__(self) -> None:
        # --- service references (populated by initialise()) ---
        self.weather_service = None
        self.trainerroad_service = None
        self.route_library_service = None
        self.analysis_service = None
        self.commute_service = None
        self.planner_service = None
        self.exploration_service = None
        self.geocoding_service = None
        self.garmin_service = None
        # SettingsService is eager — constructed immediately
        from app.services.settings_service import SettingsService
        self.settings_service: SettingsService = SettingsService()

        # --- job state ---
        self.jobs: JobRegistry = JobRegistry()

        self._initialised: bool = False

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def initialised(self) -> bool:
        return self._initialised

    def initialise(self) -> None:
        """Initialise all services (idempotent; safe to call multiple times).

        Uses wave-parallel ThreadPoolExecutor for I/O-bound service constructors:

          Wave 1 (parallel): WeatherService, TrainerRoadService, RouteLibraryService
          Wave 2 (serial):   AnalysisService (depends on WeatherService)
          Wave 3 (parallel): CommuteService, PlannerService
        """
        if self._initialised:
            return

        logger.info("Initializing services (wave-parallel)...")

        # Wave 1 — I/O-bound, no mutual dependencies
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(self._init_weather): 'weather',
                pool.submit(self._init_trainerroad): 'trainerroad',
                pool.submit(self._init_route_library): 'route_library',
            }
            for f in as_completed(futures):
                name = futures[f]
                try:
                    f.result()
                except Exception as exc:
                    logger.warning("Wave-1 service '%s' failed: %s", name, exc)

        # Wave 2 — AnalysisService depends on WeatherService
        self._init_analysis()

        # Wave 3 — parallel, depend on Wave 1 + Wave 2 results
        with ThreadPoolExecutor(max_workers=2) as pool:
            f_commute = pool.submit(self._init_commute)
            f_planner = pool.submit(self._init_planner)
            for f, name in ((f_commute, 'commute'), (f_planner, 'planner')):
                try:
                    f.result()
                except Exception as exc:
                    logger.warning("Wave-3 service '%s' failed: %s", name, exc)

        self._initialised = True
        logger.info("Services initialized successfully")

    def reset_initialisation(self) -> None:
        """Allow re-initialisation after an analysis/fetch job completes."""
        self._initialised = False

    # ------------------------------------------------------------------
    # Private per-service init helpers
    # ------------------------------------------------------------------

    def _init_weather(self) -> None:
        try:
            from app.services.weather_service import WeatherService
            self.weather_service = WeatherService()
        except Exception as exc:
            logger.error("WeatherService failed to initialize: %s", exc, exc_info=True)
            self.weather_service = None

    def _init_trainerroad(self) -> None:
        try:
            from app.services.trainerroad_service import TrainerRoadService
            self.trainerroad_service = TrainerRoadService()
        except Exception as exc:
            logger.error("TrainerRoadService failed to initialize: %s", exc, exc_info=True)
            self.trainerroad_service = None

    def _init_route_library(self) -> None:
        try:
            from app.services.route_library_service import RouteLibraryService
            self.route_library_service = RouteLibraryService()
        except Exception as exc:
            logger.error("RouteLibraryService failed to initialize: %s", exc, exc_info=True)
            self.route_library_service = None

    def _init_analysis(self) -> None:
        try:
            from app.services.analysis_service import AnalysisService
            self.analysis_service = AnalysisService(weather_service=self.weather_service)
        except Exception as exc:
            logger.error("AnalysisService failed to initialize: %s", exc, exc_info=True)
            self.analysis_service = None

    def _init_commute(self) -> None:
        try:
            from app.services.commute_service import CommuteService
            self.commute_service = CommuteService(
                weather_service=self.weather_service,
                trainerroad_service=self.trainerroad_service,
                settings_service=self.settings_service,
            )
            if self.analysis_service and self.commute_service:
                self._load_commute_data()
        except Exception as exc:
            logger.error("CommuteService failed to initialize: %s", exc, exc_info=True)
            self.commute_service = None

    def _init_planner(self) -> None:
        try:
            from app.services.planner_service import PlannerService
            self.planner_service = PlannerService(weather_service=self.weather_service)
            if self.analysis_service and self.planner_service:
                long_rides = self.analysis_service.get_long_rides()
                if long_rides:
                    self.planner_service.initialize(long_rides)
                    logger.info("PlannerService initialized with %d long rides", len(long_rides))
        except Exception as exc:
            logger.error("PlannerService failed to initialize: %s", exc, exc_info=True)
            self.planner_service = None

    def _load_commute_data(self) -> None:
        """Populate CommuteService from cached analysis results."""
        from src.config_manager import ConfigManager
        config = ConfigManager.get_instance()

        analysis_status = self.analysis_service.get_analysis_status()
        if not analysis_status.get('has_data', False):
            logger.info("No cached data available — run analysis first to enable commute recommendations")
            return

        logger.info("Loading cached analysis data...")
        try:
            route_groups = self.analysis_service.get_route_groups()
            home_location, work_location = self.analysis_service.get_locations()

            if home_location is None or work_location is None:
                from src.location_finder import Location
                try:
                    home_lat = config.get('location.home.latitude')
                    home_lon = config.get('location.home.longitude')
                    work_lat = config.get('location.work.latitude')
                    work_lon = config.get('location.work.longitude')
                    if None in (home_lat, home_lon, work_lat, work_lon):
                        raise ValueError("Missing location coordinates in config")
                    home_location = Location(lat=float(home_lat), lon=float(home_lon), name="Home", activity_count=0)
                    work_location = Location(lat=float(work_lat), lon=float(work_lon), name="Work", activity_count=0)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Invalid location coordinates in config: {exc}")

            enable_weather = config.get('weather.enabled', True)
            self.commute_service.initialize(
                route_groups=route_groups,
                home_location=home_location,
                work_location=work_location,
                enable_weather=enable_weather,
            )
            logger.info("CommuteService initialized successfully")
        except ValueError as exc:
            logger.warning("Invalid route data or config; commute service will not be available: %s", exc)
        except Exception as exc:
            logger.error("Failed to initialize commute service: %s", exc, exc_info=True)

    # ------------------------------------------------------------------
    # Lazy service accessors (for services not in the main init waves)
    # ------------------------------------------------------------------

    def get_exploration_service(self):
        """Return ExplorationService, creating it on first access."""
        if self.exploration_service is None:
            from app.services.exploration_service import ExplorationService
            self.exploration_service = ExplorationService()
        return self.exploration_service

    def get_geocoding_service(self):
        """Return GeocodingService, creating it on first access."""
        if self.geocoding_service is None:
            from app.services.geocoding_service import GeocodingService
            self.geocoding_service = GeocodingService()
        return self.geocoding_service

    def get_garmin_service(self):
        """Return GarminService, creating it on first access."""
        if self.garmin_service is None:
            from app.services.garmin_service import GarminService
            self.garmin_service = GarminService()
        return self.garmin_service
