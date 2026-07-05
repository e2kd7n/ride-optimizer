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
| `--success` | Good fit / favorable | `#3E8E63` | `#57B384` |
| `--warning` | Caution / neutral | `#C98A1D` | `#E0A63E` |
| `--danger` | Poor fit / unfavorable | `#C4483A` | `#E2695C` |

**The one rule that matters:** coral is spent in exactly one place per screen — the day's headline decision badge or its single primary CTA. Cobalt carries everything structural. This is the direct fix for the old brand's failure mode, where one indigo gradient did the job of five different signals (brand, focus ring, selection, "optimal," hover) until none of them meant anything.

Semantic colors (success/warning/danger) are functional, not brand — they signal fit/favorability and stay legible on both grounds independent of the accent hues.

---

## Type

- **Display** (headlines, decision copy, CTA labels): geometric sans — `"Century Gothic", "Avenir Next", "Futura", -apple-system, sans-serif`.
- **Body** (everything read at length, labels, meta text): the existing system UI stack — `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`. No change needed here; the existing stack was never the problem.
- **Numerals:** no separate mono face in-product. Anywhere digits line up in a column (temperature, distance, elevation, match score, hourly forecast) apply `font-variant-numeric: tabular-nums` to whichever face is already in use.

| Role | Size / weight |
|---|---|
| Display / hero decision | 2.5rem, 700 |
| Section heading | 1.5–2rem, 700 |
| Card title | 1.1–1.35rem, 700 |
| Body | 1rem, 400 |
| Caption / eyebrow | 0.72–0.78rem, 600, letter-spacing tracked |

---

## Shape & elevation

- Card radius: **16px** (up from the previous 10px/8px) — see `plans/v0.6.0/DESIGN_PRINCIPLES.md` §10 for the updated pattern library.
- Buttons and badges: fully rounded (`border-radius: 999px`), matching the mark's circular geometry.
- Shadows: quiet by default (`0 1px 2px rgba(0,0,0,0.08)`); reserve a visible lift for hover/interactive states only.

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

Not yet wired into `static/*.html` or `static/css/main.css` — those still carry the pre-rebrand indigo tokens. See `plans/v0.6.0/DESIGN_PRINCIPLES.md` §4 for the token mapping to apply when implementing.
