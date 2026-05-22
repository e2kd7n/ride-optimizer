# Cross-Platform Compatibility Analysis

**Last Updated:** 2026-05-19

## Executive Summary

This document identifies cross-platform compatibility issues in the Ride Optimizer repository and provides solutions for running scripts on Windows, macOS, and Linux (including Raspberry Pi).

## Issues Identified

### 1. Shell Scripts (`.sh` files)

**Problem:** Bash scripts don't run natively on Windows without WSL/Git Bash/Cygwin.

**Affected Scripts:**
- `scripts/run-tests.sh`
- `scripts/run-integration-tests.sh`
- `scripts/run-with-weasyprint.sh`
- `scripts/build-pi.sh`
- `scripts/weekly-maintenance.sh`
- `scripts/update-issue-priorities.sh`
- `scripts/align-labels.sh`
- `scripts/close-issue.sh`
- `scripts/reopen-integration-issues.sh`
- `scripts/sync-todos-to-issues.sh`
- `scripts/verify-issue-closures.sh`
- `cron/install_cron.sh`

**Platform-Specific Issues:**
- **Bash syntax:** `#!/bin/bash`, `set -e`, `source`, `command -v`
- **Unix commands:** `mktemp`, `grep`, `sed`, `awk`, `chmod`
- **Path separators:** Forward slashes vs backslashes
- **Color codes:** ANSI escape sequences may not work in Windows CMD
- **Date commands:** Different syntax on macOS vs Linux
- **Cron:** Not available on Windows

### 2. Python Scripts with Platform-Specific Code

**Affected Files:**

#### `main.py` (lines 50-51)
```python
if platform.system() == 'Darwin':  # macOS
    os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib:' + os.environ.get('DYLD_LIBRARY_PATH', '')
```
- **Issue:** macOS-specific WeasyPrint library path
- **Impact:** Won't affect Windows/Linux but is macOS-only

#### `scripts/menu.py` (line 69)
```python
os.system('clear' if os.name != 'nt' else 'cls')
```
- **Status:** ✅ Already cross-platform compatible

#### `scripts/weekly-maintenance.sh` (line 154)
```bash
date -u -v+7d +"%Y-%m-%d" 2>/dev/null || date -u -d "+7 days" +"%Y-%m-%d"
```
- **Issue:** macOS uses `-v+7d`, Linux uses `-d "+7 days"`
- **Impact:** Script handles this with fallback

### 3. File Permission Issues

**Problem:** `chmod` commands in scripts won't work on Windows NTFS.

**Affected:**
- `cron/install_cron.sh` - Makes scripts executable
- `scripts/menu.py` - Sets script permissions
- Security-related file permissions (0600, 0755)

### 4. Cron Jobs

**Problem:** Cron is Unix-only. Windows uses Task Scheduler.

**Affected:**
- `cron/install_cron.sh`
- `cron/daily_analysis.py`
- `cron/weather_refresh.py`
- `cron/cache_cleanup.py`
- `cron/system_health.py`

## Solutions Implemented

### Solution 1: Python Wrapper Scripts

Created cross-platform Python wrappers for commonly-used shell scripts:
- `scripts/run_tests.py` - Replaces `run-tests.sh`
- `scripts/run_integration_tests.py` - Replaces `run-integration-tests.sh`
- `scripts/update_issue_priorities.py` - Replaces `update-issue-priorities.sh`

**Benefits:**
- Work on Windows, macOS, and Linux
- No external dependencies (bash, grep, sed, etc.)
- Maintain same functionality as shell scripts
- Can be called from shell scripts for backward compatibility

### Solution 2: Platform Detection

Python scripts use `platform.system()` to detect OS:
```python
import platform

if platform.system() == 'Windows':
    # Windows-specific code
elif platform.system() == 'Darwin':
    # macOS-specific code
else:
    # Linux/Unix code
```

### Solution 3: Path Handling

Use `pathlib.Path` for cross-platform path handling:
```python
from pathlib import Path

project_root = Path(__file__).parent.parent
script_path = project_root / "scripts" / "test.py"
```

### Solution 4: Subprocess for Commands

Replace shell commands with Python equivalents:
```python
import subprocess
import shutil

# Instead of: command -v pytest
if shutil.which('pytest'):
    # pytest is available
    
# Instead of: chmod +x script.sh
if platform.system() != 'Windows':
    os.chmod(script_path, 0o755)
```

## Usage Guide

### Running Tests

**Windows:**
```cmd
python scripts/run_tests.py all
python scripts/run_tests.py unit
python scripts/run_tests.py coverage
```

**macOS/Linux:**
```bash
# Use Python wrapper (recommended)
python scripts/run_tests.py all

# Or use shell script
./scripts/run-tests.sh all
```

### Running Integration Tests

**Windows:**
```cmd
python scripts/run_integration_tests.py
```

**macOS/Linux:**
```bash
python scripts/run_integration_tests.py
# Or: ./scripts/run-integration-tests.sh
```

### GitHub Issue Management

**Windows:**
```cmd
python scripts/update_issue_priorities.py
python scripts/update_issue_priorities.py --auto-close
```

**macOS/Linux:**
```bash
python scripts/update_issue_priorities.py
# Or: ./scripts/update-issue-priorities.sh
```

### Cron Jobs (Unix-only)

**Linux/Raspberry Pi:**
```bash
cd /path/to/ride-optimizer
./cron/install_cron.sh
```

**Windows Alternative:**
Use Task Scheduler to run Python scripts:
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., daily at 2 AM)
4. Action: Start a program
5. Program: `python.exe`
6. Arguments: `C:\path\to\ride-optimizer\cron\daily_analysis.py`
7. Start in: `C:\path\to\ride-optimizer`

## Remaining Platform-Specific Scripts

These scripts remain Unix-only due to their nature:

### GitHub Integration Scripts
- `scripts/align-labels.sh` - Requires `gh` CLI
- `scripts/close-issue.sh` - Requires `gh` CLI
- `scripts/sync-todos-to-issues.sh` - Requires `gh` CLI
- `scripts/verify-issue-closures.sh` - Requires `gh` CLI

**Windows Users:** Install GitHub CLI for Windows and use Git Bash or WSL to run these scripts.

### Build Scripts
- `scripts/build-pi.sh` - Raspberry Pi specific
- `scripts/run-with-weasyprint.sh` - macOS specific

**Note:** These are environment-specific and don't need Windows equivalents.

### Maintenance Scripts
- `scripts/weekly-maintenance.sh` - Uses many Unix tools

**Windows Alternative:** Run individual Python scripts manually or create a PowerShell equivalent.

## Testing Checklist

- [x] Identify all shell scripts
- [x] Identify platform-specific Python code
- [x] Create Python wrappers for critical scripts
- [ ] Test on Windows 10/11
- [ ] Test on macOS (Intel and Apple Silicon)
- [ ] Test on Linux (Ubuntu/Debian)
- [ ] Test on Raspberry Pi OS
- [ ] Document Windows Task Scheduler setup
- [ ] Update README with cross-platform instructions

## Recommendations

### For Development
1. **Use Python wrappers** when available - they work everywhere
2. **Keep shell scripts** for Unix environments - they're more efficient
3. **Test on target platform** before committing changes
4. **Use `pathlib`** instead of string concatenation for paths
5. **Avoid platform-specific commands** in new scripts

### For Windows Users
1. **Install Git for Windows** - includes Git Bash for running shell scripts
2. **Use WSL2** for full Linux compatibility
3. **Install GitHub CLI** for Windows for issue management
4. **Use Python wrappers** for testing and common tasks

### For Raspberry Pi Users
1. **Use shell scripts** - they're optimized for Unix
2. **Install cron jobs** for automated tasks
3. **Monitor logs** in `logs/` directory
4. **Use `build-pi.sh`** for container builds

## Future Improvements

1. **Create PowerShell equivalents** for maintenance scripts
2. **Add Windows Task Scheduler templates** for cron jobs
3. **Improve error messages** for missing dependencies
4. **Add platform detection** to installation scripts
5. **Create unified CLI** that works on all platforms

## Support

For platform-specific issues:
- **Windows:** Check Git Bash, WSL, or Python wrapper availability
- **macOS:** Ensure Homebrew packages are installed
- **Linux:** Verify bash and standard Unix tools are available
- **Raspberry Pi:** Check ARM-specific dependencies

## References

- Python `platform` module: https://docs.python.org/3/library/platform.html
- Python `pathlib` module: https://docs.python.org/3/library/pathlib.html
- GitHub CLI: https://cli.github.com/
- Windows Task Scheduler: https://docs.microsoft.com/en-us/windows/win32/taskschd/