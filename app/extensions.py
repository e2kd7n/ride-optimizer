"""Shared Flask extension instances.

Created unbound here and wired to the app via ``init_app()`` in
``app.factory.create_app`` (the standard app-factory pattern). Blueprint
modules import ``limiter`` directly so they can decorate individual routes
with ``@limiter.limit(...)`` at import time.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
    strategy="fixed-window",
)
