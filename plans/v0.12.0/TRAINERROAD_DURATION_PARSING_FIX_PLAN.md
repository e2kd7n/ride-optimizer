# TrainerRoad Duration Parsing Fix Plan

## Top-Level Overview
Fix TrainerRoad workout duration parsing so upcoming workouts show duration reliably in the settings table. The change should remain narrowly scoped to TrainerRoad ICS normalization and test coverage: timed events should use calendar start and end times, date-only events should derive duration from the workout title when possible, and unsupported cases should continue surfacing no duration.

## Sub-Tasks

### 1. Correct TrainerRoad duration normalization
- **Intent** — Make [`TrainerRoadService._parse_event()`](../../app/services/trainerroad_service.py:201) compute `duration_minutes` for both timed and date-only events using the intended fallback behavior.
- **Expected Outcomes** — Timed TrainerRoad events produce minute durations from `DTSTART` and `DTEND`; date-only events can populate duration from title prefixes like `2:00 - Workout Name`; unknown date-only durations remain blank.
- **Todo List**
  1. Inspect the existing event parsing flow in [`TrainerRoadService._parse_event()`](../../app/services/trainerroad_service.py:201).
  2. Replace the fragile duration calculation with explicit timed-event handling.
  3. Add a title-based duration extraction fallback for date-only events.
  4. Preserve current behavior for missing or unparseable duration values.
- **Relevant Context** — [`app/services/trainerroad_service.py`](../../app/services/trainerroad_service.py), [`TrainerRoadService.parse_ics_feed()`](../../app/services/trainerroad_service.py:174)
- **Status** — [x] done

### 2. Add focused regression coverage
- **Intent** — Lock in the parsing behavior so future TrainerRoad feed variations do not regress duration handling.
- **Expected Outcomes** — Unit tests cover timed ICS events, date-only title-derived durations, and unknown-duration fallbacks.
- **Todo List**
  1. Follow the existing TrainerRoad unit test structure in [`tests/test_trainerroad_service.py`](../../tests/test_trainerroad_service.py).
  2. Add assertions for timed duration parsing.
  3. Add assertions for date-only events with duration prefixes in the summary.
  4. Add assertions for date-only events without derivable duration.
- **Relevant Context** — [`tests/test_trainerroad_service.py`](../../tests/test_trainerroad_service.py)
- **Status** — [x] done

### 3. Validate end-to-end data shape
- **Intent** — Confirm the backend change is sufficient for the existing UI rendering path.
- **Expected Outcomes** — Relevant tests pass and the existing settings table renderer can display parsed durations without frontend changes.
- **Todo List**
  1. Run the TrainerRoad unit tests.
  2. Verify the workouts response still exposes `duration_minutes` consumed by [`loadTrainerRoadWorkouts()`](../../static/settings.html:1291).
  3. Leave the frontend unchanged unless validation reveals a backend-contract issue.
- **Relevant Context** — [`static/settings.html`](../../static/settings.html), [`loadTrainerRoadWorkouts()`](../../static/settings.html:1291)
- **Status** — [x] done
