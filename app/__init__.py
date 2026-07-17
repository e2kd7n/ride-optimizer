"""
The ``app`` package.

The Flask application factory lives in :mod:`app.factory`
(``app.factory.create_app``) — it wires up the real
:class:`~app.container.ServiceContainer`, blueprints, CSRF protection, and
security headers, and is used by both ``launch.py``/``wsgi.py`` and the test
suite. There is no separate factory here; see #460 for the history (this
module previously defined a second, divergent ``create_app()`` used only by
tests, which has been removed in favor of the production factory).
"""
