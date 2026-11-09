"""Escape free text (Strava ride/route names, place labels) for Folium maps.

Folium embeds tooltip text and popup HTML *raw* inside JavaScript template
literals, e.g. ``bindTooltip(`<div>{{ text }}</div>`)`` and
``$(`{{ popup_html }}`)``. ``html.escape`` stops a name from closing the
``<script>`` block, but a backtick would end the template literal and ``${…}``
would be evaluated as JavaScript. Encode those (and backslash, which would
otherwise form escape sequences) as HTML entities too: they render identically
once Leaflet puts the string into the DOM.
"""
from html import escape


def folium_escape(value) -> str:
    """HTML-escape ``value`` and make it inert inside a JS template literal."""
    return (
        escape(str(value))
        .replace('\\', '&#92;')
        .replace('`', '&#96;')
        .replace('$', '&#36;')
    )
