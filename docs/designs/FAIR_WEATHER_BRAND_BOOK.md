# Fair Weather — Brand Book

**Status:** Current / Active brand identity
**Adopted:** 2026-07-05
**Supersedes:** the unstyled Bootstrap defaults (indigo/purple `#667eea → #764ba2` gradient, system font stack, no logo) that shipped through v0.16.0
**Live references:** [`BRAND_CONCEPTS_COMPARISON.html`](BRAND_CONCEPTS_COMPARISON.html) (the three candidate identities reviewed before this one was chosen) and [`FAIR_WEATHER_BRAND_BOOK.html`](FAIR_WEATHER_BRAND_BOOK.html) (interactive logo/color/type/screen mockups — open either file directly in a browser)

This document is the text-readable spec for implementers and agents. The HTML files above are the visual reference; this file is the source of truth when the two disagree.

---

## Why Fair Weather

Three directions were pitched — **Instrument** (dark cyclocomputer aesthetic), **Contour** (warm topographic/editorial), and **Fair Weather** (bright, weather-forward) — see `BRAND_CONCEPTS_COMPARISON.html` for all three. Fair Weather was selected. Its thesis: the app exists to answer one question — *is today a good day to ride, and which route fits it* — so the brand should read as bright, confident, and decision-first rather than data-dense or decorative.

---

## Logo

**Mark:** a circle with eight radiating ticks. It reads simultaneously as a wheel hub and a sun, because the product sits at exactly that intersection (cycling + weather). Defined as an inline SVG using `stroke="currentColor"` so a single source recolors correctly for the navbar, favicon, and PWA home-screen icon.

```html
<svg viewBox="0 0 48 48" fill="none">
  <circle cx="24" cy="24" r="12" stroke="currentColor" stroke-width="3.4"/>
  <g stroke="currentColor" stroke-width="3.4" stroke-linecap="round">
    <line x1="24" y1="2" x2="24" y2="8"/><line x1="24" y1="40" x2="24" y2="46"/>
    <line x1="2" y1="24" x2="8" y2="24"/><line x1="40" y1="24" x2="46" y2="24"/>
    <line x1="8.3" y1="8.3" x2="12.5" y2="12.5"/><line x1="35.5" y1="35.5" x2="39.7" y2="39.7"/>
    <line x1="39.7" y1="8.3" x2="35.5" y2="12.5"/><line x1="12.5" y1="35.5" x2="8.3" y2="39.7"/>
  </g>
</svg>
```

**Minimum size:** below 24px, drop the four diagonal rays and keep only the circle plus the four cardinal ticks — it still reads as the mark without turning into noise at favicon scale (16px).

**Lockups:**
- **Primary (horizontal):** mark + "Ride" (ink) + "Optimizer" (cobalt accent) — default for navbars and headers.
- **Reversed:** full white lockup, for cobalt or dark/night surfaces.
- **Stacked:** mark above the wordmark, tagline below — for square contexts (app icon splash, social/share cards).
- **Mark only:** the app icon / favicon source, inside a coral rounded-square (`border-radius: 22%`) at large sizes.

**Tagline:** "Know before you go."

---

## Color

Two grounds, not one inverted into the other: **Day** is an overcast-bright sky, **Night** is a clear one. Accents shift in *brightness*, not just hue, to stay correct on each ground.

| Token | Role | Day | Night |
|---|---|---|---|
| `--bg` | Ground | `#F3F6F7` | `#0B1620` |
| `--surface` | Card surface | `#FFFFFF` | `#122232` |
| `--surface-2` | Secondary surface (nav, footer) | `#EDF2F4` | `#16283A` |
| `--ink` | Primary text | `#0F2233` | `#EAF0F3` |
| `--ink-soft` | Secondary text | `#5B7686` | `#8FA6B4` |
| `--line` | Borders / dividers / hover | `#DCE3E6` | `#223243` |
| `--accent` | Cobalt — structure, links, brand, info | `#0B6FA6` | `#4FB3E8` |
| `--accent-warm` | Coral — **one** CTA/badge per screen only | `#F2662D` | `#FF8A57` |
| `--success` | Good fit / favorable | `#2D7A52` | `#57B384` |
| `--warning` | Caution / neutral | `#C98A1D` | `#E0A63E` |
| `--danger` | Poor fit / unfavorable | `#C4483A` | `#E2695C` |

**The one rule that matters:** coral is spent in exactly one place per screen — the day's headline decision badge or its single primary CTA. Cobalt carries everything structural. This is the direct fix for the old brand's failure mode, where one indigo gradient did the job of five different signals (brand, focus ring, selection, "optimal," hover) until none of them meant anything.

Semantic colors (success/warning/danger) are functional, not brand — they signal fit/favorability and stay legible on both grounds independent of the accent hues.

**Text on a fill belongs to the fill.** Anything filled with an accent or semantic colour (buttons, badges, the weather banner) takes its text from the matching `--on-*` token, never a hardcoded `#fff`:

| Token | Day | Night |
|---|---|---|
| `--on-accent` | `#FFFFFF` (5.5:1) | `#0B1620` (7.8:1) |
| `--on-accent-warm` | `#0F2233` (5.2:1) | `#0B1620` (7.9:1) |
| `--on-success` | `#FFFFFF` (5.2:1) | `#0B1620` (7.1:1) |
| `--on-warning` | `#0F2233` (5.5:1) | `#0B1620` (8.4:1) |
| `--on-danger` | `#FFFFFF` (4.8:1) | `#0B1620` (5.6:1) |

White on the Night accents measured 2.2–3.3:1, and white on Day coral 3.1:1, so every primary button, CTA and score badge was below WCAG AA in at least one theme.

---

## Type

- **Display** (headlines, decision copy, CTA labels): geometric sans — `"Century Gothic", "Avenir Next", "Futura", -apple-system, sans-serif`.
- **Body** (everything read at length, labels, meta text): the existing system UI stack — `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`. No change needed here; the existing stack was never the problem.
- **Numerals:** no separate mono face in-product. Anywhere digits line up in a column (temperature, distance, elevation, match score, hourly forecast) apply `font-variant-numeric: tabular-nums` to whichever face is already in use.

| Role | Size / weight |
|---|---|
| Display / hero decision | 2.5rem, 700 |
| Section heading | 1.5–2rem, 700 |
| Card title | 1.25rem (`--font-size-md`), 600 |
| Glance number | 3rem / 2.5rem on phones, Barlow Condensed 600 (see Glance layer) |
| Body | 1rem, 400 |
| Caption / eyebrow | 0.72–0.78rem, 600, letter-spacing tracked |

---

## Shape & elevation

- Card radius: **16px** (up from the previous 10px/8px) — see `plans/v0.6.0/DESIGN_PRINCIPLES.md` §10 for the updated pattern library. Nested elements use 8px (see Glance layer › Shape).
- Buttons and badges: fully rounded (`border-radius: 999px`), matching the mark's circular geometry.
- Shadows: quiet by default (`0 1px 2px rgba(0,0,0,0.08)`); reserve a visible lift for hover on things you can actually click (G5).

---

## Glance layer

**Adopted:** 2026-10-25. Borrowed from the Connect IQ data-field design language (`ciq-edge/design/DESIGN.md`), where every field has to answer one question at 20 mph. The app answers the same kind of question ("is this a good ride today?"), so its decision moments use the same grammar. Fair Weather still owns the page (grounds, cobalt, coral, type). The glance layer only governs **verdicts and the numbers behind them**.

### Principles

| # | Principle | In the app |
|---|---|---|
| G1 | **One big signal** | A decision card leads with one coloured panel: verdict word + icon on the left, one big number on the right. Everything else sits below it. |
| G2 | **Colour + word + icon** | A verdict is never colour alone. `Good` / `Fair` / `Poor` always travel with their icon, so they still read for colour-blind riders and on a washed-out phone in sun. |
| G3 | **One score, one scale** | Every 0–100 score goes through `scoreToRating()` (≥70 good, ≥50 fair, else poor) and the `VERDICTS` table in `dashboard.js`. Don't add a second threshold ladder for the same score. |
| G4 | **Same panel day and night** | Verdict fills don't change with the theme. Only the page around them switches. |
| G5 | **Calm display** | Nothing jumps. A card doesn't lift or slide under the pointer unless it's a link (`a.card`, `.card-interactive`), and cards don't fade in on load. Hover feedback is border and shadow only, never `transform`. |
| G6 | **LABEL / value** | Secondary facts are cells: an upper-case 12px tracked label over a condensed tabular value, split by 1px hairlines, with no boxes. No icon-prefixed runs of numbers. |

### Verdict fills

Fixed tokens, the same on both grounds. Each carries its own text colour, and every pair is ≥ 5:1.

| Rating | Word | Icon | Fill token | Fill | Text | Contrast |
|---|---|---|---|---|---|---|
| good | Good | `bi-check-circle-fill` | `--verdict-good` | `#188038` | `#FFFFFF` | 5.0:1 |
| warn | Fair | `bi-exclamation-triangle-fill` | `--verdict-warn` | `#F2A900` | `#111111` | 9.4:1 |
| bad | Poor | `bi-x-circle-fill` | `--verdict-bad` | `#C62828` | `#FFFFFF` | 5.6:1 |
| neutral | — | none | `--verdict-neutral` | `#455A64` | `#FFFFFF` | 7.2:1 |

- **Fills vs marks.** Panels and chips use the `--verdict-*` fills. A small glyph sitting on the page ground (the Route Status icons) keeps the theme-shifted `--success` / `--warning` / `--danger`, because amber as a glyph on a white page would fall well under 3:1.
- **Neutral never looks like a verdict.** "No data", "Recommended" and other states that give no advice use slate or `bg-secondary`, with no check and no cross.
- **Coral is not a verdict.** It stays the one CTA per screen (see Color). A verdict panel and the coral CTA can share a card, because they say different things.

### Numerals

Big and tabular numbers (hero score, temperature, cell values, stat cards, route stats) use **Barlow Condensed SemiBold** via `--font-numeric`. It's the same face the CIQ fields bundle for their digits. It's self-hosted at `static/fonts/` (SIL OFL 1.1, licence alongside) so the Pi PWA renders it offline and CSP `font-src 'self'` covers it. Body copy and words stay on the existing stacks.

### Components

| Component | Classes | Spec |
|---|---|---|
| Glance panel | `.glance-panel.verdict-<rating>` | 16px inset, `--radius-sm`. `.glance-word` (24px display, upper case, icon gap 8px) and `.glance-sub` (route name) left; `.glance-num` (48px, 40px on phones) + `.glance-unit` right, on one baseline. Carries `role="status"` and an `aria-label` that spells out the verdict and score. |
| Cells | `.glance-cells > .glance-cell > .glance-label + .glance-value` | Auto-fit columns ≥ 96px (2 per row on phones), 16px inset between cells, 1px `--line` hairline. A unit inside the value is `.glance-unit`. |
| Verdict chip | `verdictChip(rating, text)` → `.verdict-chip.verdict-<rating>` | Pill, 24px tall, icon + word (+ optional `.glance-chip-num`). The compact form of the panel, for lists and secondary cards. |

### Shape

Three radii only: `--radius-sm` 8px (anything nested in a card, alerts, toasts, list rows, hourly cells), `--radius-md` 16px (cards), `--radius-pill` (buttons, badges, chips). 8px nested inside a 16px card with a 16px inset keeps the corners concentric. The 4px and 6px radii are retired.

### Route palette

Map polylines, legend dots and chart series take their colours from one fixed palette. These are the same values in `static/css/main.css` (`.c-*`), `static/js/routes.js`, and `app/api/maps_api.py::get_route_color`.

| Use | Colours |
|---|---|
| **Identity** (route 1, route 2…, chart series, travel direction) | Cobalt `#0B6FA6`, Teal `#1F8A8A`, Purple `#7A4FA0`, Orange `#E8702A`, Magenta `#A8457E`, Amber `#C98A1D`, Brown `#8A5A3C`, Slate `#5B7686` |
| **Ordered scale** (Routes page distance and recency legends) | Green `#2D7A52`, Amber `#C98A1D`, Orange `#E8702A` and Red `#C4483A`, with Cobalt for the newest and Slate for the oldest |
| **Score** (a map line coloured by its match score) | The verdict fills above, on the same 70/50 scale |

Identity colours never use the verdict green or red, so a route can't read as Good or Poor just because of its place in a list. Commutes are cobalt to work and teal home, on both the map and the cards. Bootstrap's default `#007bff`, `#28a745` and related colours are retired.

---

## Content rules introduced with this brand

Two product-level rules were adopted alongside the visual identity (both now in `plans/v0.6.0/DESIGN_PRINCIPLES.md`):

1. **Weather cards show wind and precipitation whenever available**, not temperature alone. In a single hero/summary card, show the value even at zero (confirming "0% chance of rain" is useful). In a repeated list (hourly strip), omit a field per-cell only when its value is trivial, to avoid clutter — see §2.
2. **Map controls/lists sit beside the map on `lg`+ viewports**, not stacked above or below it — see §3. This formalizes recommendations already made ad hoc in issues [#365](https://github.com/e2kd7n/ride-optimizer/issues/365) and [#367](https://github.com/e2kd7n/ride-optimizer/issues/367); Route Detail's existing `col-lg-5`/`col-lg-7` split is the reference implementation already in the codebase.

---

## Reference screens

`FAIR_WEATHER_BRAND_BOOK.html` includes full Day/Night mockups of three screens, built from the app's real content model (Strava routes, TrainerRoad workout fit, weather):

- **Today** — hero decision card (match score, headline, CTA) + ranked route list with good-fit/caution badges.
- **Weather** — current conditions + hourly forecast strip with wind and precipitation per hour.
- **Route** — stat header, elevation sparkline, TrainerRoad workout-fit callout.

---

## Rollout

Migration is complete — `static/css/main.css` and every `static/*.html` page carry the Day/Night tokens above, including the dark-mode override block (`main.css:127-156`); no pre-rebrand indigo gradient remains. Treat `main.css` as the reference implementation of these tokens; `plans/v0.6.0/DESIGN_PRINCIPLES.md` §4 gives the flattened token reference for implementers.
