# ⛔ DEPRECATED CLI SYSTEM - DO NOT USE ⛔

## ⚠️ CRITICAL WARNING ⚠️

**THIS DIRECTORY CONTAINS DEPRECATED CODE THAT SHOULD NEVER BE MODIFIED**

## What Happened

Epic #237 (UI/UX Redesign) was **mistakenly implemented in this deprecated system** instead of the active web application, wasting significant development time and effort.

**Date of Mistake:** May 2026  
**Impact:** 40-60 hours of wasted work  
**Root Cause:** Insufficient deprecation warnings

## The Mistake

1. **Epic #237** (14 issues, comprehensive QA) was implemented in `templates/report_template.html`
2. This template is part of the **DEPRECATED CLI system**
3. The **active web application** uses `static/*.html` files served by `launch.py`
4. Result: All Epic #237 improvements are NOT in the production web app

## Product Vision (FINAL DECISION)

**The product is a WEB APPLICATION, not a CLI tool.**

- ✅ **Active System:** `launch.py` + `static/` files
- ❌ **Deprecated System:** `main.py` + `templates/` files (THIS DIRECTORY)

## Why This Directory Exists

This directory is archived for historical reference only. The CLI report generation system (`main.py` + templates) has been superseded by the web application architecture.

## What's in This Directory

- `templates/report_template.html` - 328KB deprecated template
- `templates/report_template.html.backup` - Backup of deprecated template
- Epic #237 implementations (navigation, accessibility, mobile optimizations)

**ALL OF THIS IS DEPRECATED AND SHOULD NOT BE USED**

## If You Need to Make UI/UX Changes

### ✅ CORRECT: Edit These Files
```
static/dashboard.html
static/routes.html
static/commute.html
static/planner.html
static/css/main.css
static/js/*.js
```

### ❌ WRONG: Do NOT Edit These Files
```
archive/deprecated_cli_system/templates/*  (THIS DIRECTORY)
main.py (CLI tool - deprecated for UI work)
```

## Architecture Clarity

### Web Application (ACTIVE)
```
User → Browser → launch.py (port 8083) → static/*.html → app/services/*.py
```

### CLI Report Generator (DEPRECATED)
```
User → main.py --analyze → templates/report_template.html → output/report.html
```

## Lessons Learned

1. **Deprecation warnings were insufficient** - Need stronger barriers
2. **Two systems caused confusion** - Should have been removed earlier
3. **Epic #237 was misdirected** - Implemented in wrong codebase
4. **Cost:** 40-60 hours of work needs to be redone for web app

## Prevention Measures

1. ✅ Archived deprecated templates to `archive/deprecated_cli_system/`
2. ✅ Added this comprehensive warning file
3. ✅ Updated `main.py` with prominent warnings
4. ✅ Updated `AGENTS.md` with architecture clarity
5. ✅ Created issue #257 to port Epic #237 to correct system

## If You're Reading This

**STOP. Do not modify files in this directory.**

If you need to make UI/UX changes, go to `static/` directory instead.

If you're implementing an issue and it references `templates/`, **STOP and ask for clarification** - the issue may be misdirected.

---

**Last Updated:** 2026-05-09  
**Reason for Archive:** Prevent future misdirected development work  
**Related Issue:** #257 - Sync Epic #237 to correct system