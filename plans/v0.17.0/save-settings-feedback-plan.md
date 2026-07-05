# Save Settings Feedback Plan

## Overview

**Goal:** The "Save Settings" button must give the user clear, immediate feedback when their changes are saved.

**Problem:** [`saveSettings()`](../../static/settings.html:774) is async. The button gives no indication that the save is in progress or completed, making clicks feel ignored.

**Scope:** One file — [`static/settings.html`](../../static/settings.html). No new infrastructure needed.

**Approach:** Change the button label to "Save Complete" after the save finishes, then restore it after a short delay.

---

## Sub-Task 1 — Change button text to "Save Complete" after save

**Intent:** After `saveSettings()` completes, update the button label to "Save Complete" so the user can see their action had effect. Restore the original label after a short pause.

**Expected Outcomes:**
- After clicking Save and the async work completes, the button reads "✓ Save Complete"
- After ~2 seconds, the button text reverts to the original "Save Settings" label
- No toast, no spinner, no disabling — just the button text change

**Todo List:**
1. At the end of `saveSettings()` (after `clearUnsavedChanges()`, around line 806), grab the button by `document.getElementById('save-settings')`
2. Store the original `innerHTML`, then set it to `'<i class="bi bi-check-circle" aria-hidden="true"></i> Save Complete'`
3. After 2000ms (`setTimeout`), restore the button's original `innerHTML`

**Relevant Context:**
- [`static/settings.html:774`](../../static/settings.html:774) — `saveSettings()` async function
- [`static/settings.html:546`](../../static/settings.html:546) — Save button HTML (`id="save-settings"`, uses Bootstrap icon)
- [`static/settings.html:806`](../../static/settings.html:806) — `clearUnsavedChanges()` call — insert feedback immediately after this

**Status:** `[x] done`
