# CLI Script Style Guide

**Version:** 1.0
**Status:** Active

---

## Overview

`scripts/` is the operator-facing surface of this project — the thing a human
watches scroll by during a Pi deploy, a build, or incident response. Before
this guide, `scripts/` had no shared color/UI toolkit: a spot-check of
`pi-auto-update.sh` and `build-pi.sh`, two of the most-run scripts (the
deploy/update path), showed nothing but plain `echo`/`log()` lines with no
visual hierarchy or progress feedback during slow operations (image pulls,
health-check polling, builds).

This guide extends the Fair Weather brand
(`docs/designs/FAIR_WEATHER_BRAND_BOOK.md`) to the terminal — the same
hierarchy the app's UI uses, translated into ANSI output. It does not
introduce a new toolkit — `scripts/utilities.sh` already implements
everything specified here (`section`, `steps_init`/`step`,
`start_spinner`/`stop_spinner`, `progress_bar`, `timer_start`/`timer_end`,
`wait_for`). The job is **consistent adoption** across `scripts/`, not
invention (#551).

Reference implementation: `scripts/pi-auto-update.sh`. When in doubt, look at
what it does and match it.

---

## 1. Color Palette

`scripts/utilities.sh` exports the 8-color ANSI baseline (`RED`, `GREEN`,
`YELLOW`, `BLUE`, `CYAN`, `BOLD`, `DIM`, `NC`) — a terminal-safe approximation
of the Fair Weather semantic tokens, since 24-bit true-color escapes break on
the Pi's default console and over plain SSH without a truecolor-aware `$TERM`:

| Token | Use for | Brand book equivalent |
|---|---|---|
| `GREEN` | Success, completion, healthy state | `--success` |
| `YELLOW` | Warnings, non-fatal issues, things needing attention | `--warning` |
| `RED` | Errors, failures, destructive-action prompts | `--danger` |
| `CYAN` | Section headers, structural chrome | `--accent` (cobalt) |
| `BLUE` | Informational body text, secondary detail | `--accent` (cobalt), softer weight |
| `BOLD` | Emphasis, headings, key values | brand book's heavier heading weights |
| `DIM` | Metadata: timestamps, byte counts, file counts | de-emphasized text |

Coral (`--accent-warm`) has no 8-color analog and is intentionally unused
here — in the app it's spent in exactly one place per screen (the headline
CTA); a terminal has no equivalent single-focal-point concept, so mapping it
to any ANSI color would just dilute it back into "another color scripts use,"
the exact failure mode the brand book was designed to avoid.

**Never use raw ANSI escapes inline.** Every script that prints color must
`source "$SCRIPT_DIR/utilities.sh"` and use its exported variables — no
`RED='\033[0;31m'` copy-pasted locally. This is what lets a future palette
change happen in one file instead of dozens.

## 2. Status Language

Pair every color with a shape, never color alone, so colorblind operators and
`NO_COLOR`/piped-output cases still get the signal:

| Meaning | Glyph | Example |
|---|---|---|
| Success / done | `✓` (green) | `  ✓  All deployment secrets present.` |
| Failure / blocking | `✗` or `❌` (red) | `❌ Pull failed — network issue or image not yet published.` |
| Warning / needs attention | `⚠️` (yellow) | `⚠️  Disk usage is 82% — consider running: podman image prune -a` |
| Informational | `ℹ️` or a domain emoji (blue) | `ℹ️  Image unchanged — containers not restarted.` |
| In progress | animated braille spinner via `start_spinner` | `⠋  Pulling ghcr.io/e2kd7n/ride-optimizer:latest` |

## 3. Section Headers ("recipe cards")

Use `section "Title" [emoji]` from `utilities.sh` for every major phase of a
script — a title, an underline rule, breathing room above and below. A script
with more than ~30 lines of output and no `section` calls needs this pass.

```bash
section "Pulling Image" "📥"
```

Keep a **small, consistent emoji vocabulary** per action type rather than
picking a new one per script:

| Action | Emoji |
|---|---|
| Deploy / ship | 🚀 |
| Pre-flight / check | 🔍 |
| Auth / secrets | 🔐 |
| Download / pull | 📥 |
| Package / build artifact | 📦 |
| Cleanup | 🧹 |
| Health / diagnostics | 🩺 |
| Issue listing / triage | 📋 |
| Notifications | 🔔 |
| Test suite / test run | 🧪 |
| Summary / done | 🚲 (reserve for final summaries, or a script's own top-level title banner) |

If a script needs an emoji not listed here, add it to this table in the same
PR rather than inventing a one-off.

## 4. Progress Feedback

Any operation that blocks for more than ~1-2 seconds (GHCR pulls, health-check
polling, `podman`/`podman-compose` commands) must show the user *something is
happening*:

- **Single blocking command** → `start_spinner "message"` / `stop_spinner [ok|fail]`
- **Polling until a condition is true** (e.g. waiting for the health check to
  go healthy) → `wait_for "desc" <timeout> <interval> <cmd>`
- **Iterating a known number of items** → `progress_bar`
- **Multi-step sequential procedure** → `steps_init <n>` / `step "description"`
  so the operator always knows `[3/7]` where they are
- **Anything worth reporting duration for** (builds, pulls) → `timer_start` /
  `timer_end`

A script that runs a slow command with bare output and no spinner or step
indicator needs this pass.

## 5. Confirmation & Destructive Actions

Scripts that can lose data or state (cache/log wipes, force-pushing secrets,
overwriting a running deployment) must:

1. Explain what will happen and what's about to be affected (counts, paths,
   sizes — not just "are you sure?")
2. Default to the safe choice on bare Enter (`[y/N]`, never `[Y/n]`, for
   anything destructive)
3. Use `RED`/`⚠️` for the prompt itself so it reads as different from routine
   output

`build-pi.sh`'s local-build warning (explaining the image will be silently
overwritten by the next auto-update, before it ever prompts) is a good model:
it names the risk before asking for confirmation, not after.

## 6. Accessibility & Non-Interactive Contexts

- **Respect `NO_COLOR`.** If `$NO_COLOR` is set, or stdout is not a TTY
  (piped into a log file, running under cron/systemd, captured by CI), color
  codes and the animated spinner degrade gracefully — plain text with the
  `✓`/`✗`/`⚠️` glyphs still carries the signal. `utilities.sh` handles this
  automatically; scripts don't need their own TTY checks. This matters in
  practice: `pi-auto-update.sh` runs unattended under a systemd timer with
  `StandardOutput=journal` — no TTY at all.
- **Never require a spinner or progress bar to understand what happened** —
  the final state (`✓`/`✗` + message) must be legible even with all
  animation stripped.
- **Keep line length reasonable** and avoid wide ASCII-art tables that wrap
  badly over SSH at 80 columns.

## 7. What "done" looks like

A script fully following this guide:

- Sources `scripts/utilities.sh` and uses only its exported color/UI helpers
  — no inline ANSI
- Wraps each logical phase in `section "..." "emoji"` using the vocabulary in §3
- Shows a spinner, step counter, or progress bar for anything slow (§4)
- Prints a final `section "Summary" "🚲"` recapping what happened
- Pairs every color with a glyph (§2)
- Confirms before anything destructive, defaulting safe (§5)

`scripts/pi-auto-update.sh` and `scripts/build-pi.sh` are the current
reference implementations; the rest of `scripts/` has not yet been brought up
to this standard — see #551 for the follow-up audit.

---

## Related Documentation

- [Fair Weather Brand Book](../designs/FAIR_WEATHER_BRAND_BOOK.md) — source of
  truth for the color palette in §1
- [`scripts/utilities.sh`](../../scripts/utilities.sh) — the implementation of
  every helper referenced above
- [`scripts/README.md`](../../scripts/README.md) — inventory of all scripts
