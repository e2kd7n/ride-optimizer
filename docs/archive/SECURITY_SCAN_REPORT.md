# Security Scan Report

**Date:** 2026-03-26  
**Tools Used:** Bandit 1.9.4, pip-audit 2.10.0  
**Status:** ⚠️ 3 Security Issues Found

## Executive Summary

Comprehensive security scanning identified **3 actionable security issues**:
- **1 HIGH priority** - Vulnerable dependencies requiring immediate upgrade
- **1 MEDIUM priority** - Weak hash algorithm in cache keys
- **1 LOW priority** - Code quality improvements for exception handling

## Scan Results

### Bandit Static Analysis

**Total Issues:** 9  
- **HIGH Severity:** 2 (MD5 hash usage)
- **MEDIUM Severity:** 1 (false positive - JavaScript, not SQL)
- **LOW Severity:** 6 (exception handling, XML parsing)

### Dependency Vulnerability Scan (pip-audit)

**Vulnerable Packages:** 3  
- **requests 2.32.5** - CVE-2026-25645 (HIGH)
- **tornado 6.5.4** - CVE-2026-31958 + GHSA-78cv-mqj4-43f7 (MEDIUM)
- **pygments 2.19.2** - CVE-2026-4539 (LOW, no fix available)

## Detailed Findings

### 🔴 HIGH Priority

#### Issue #60: Vulnerable Dependencies
**Packages:** requests, tornado  
**Action:** Upgrade immediately

**requests 2.32.5 → 2.33.0**
- CVE-2026-25645: Predictable temp file in `extract_zipped_paths()`
- Impact: Local attacker could inject malicious files
- Note: Standard usage NOT affected

**tornado 6.5.4 → 6.5.5**
- CVE-2026-31958: DoS via large multipart bodies
- GHSA-78cv-mqj4-43f7: Cookie injection via semicolons
- Impact: Used by Jupyter dependencies

**Fix:**
```bash
pip install --upgrade 'requests>=2.33.0' 'tornado>=6.5.5'
```

### 🟡 MEDIUM Priority

#### Issue #59: MD5 Hash Usage
**Files:** src/route_analyzer.py:286, src/weather_fetcher.py:522  
**CWE:** CWE-327 - Weak Cryptographic Algorithm

**Problem:** MD5 used for cache key generation

**Fix:**
```python
# Replace MD5 with SHA256
cache_key = hashlib.sha256(key_str.encode()).hexdigest()
```

**Impact:** Low (caching only, not security), but eliminates scanner warnings

### 🟢 LOW Priority

#### Issue #61: Bare Exception Handling
**Files:** 5 locations across codebase  
**Issue:** Bare `except:` blocks hide bugs

**Locations:**
1. main.py:150
2. src/data_fetcher.py:203
3. src/long_ride_analyzer.py:256
4. src/long_ride_analyzer.py:290
5. src/route_analyzer.py:893

**Fix:** Use specific exception types and add logging

#### XML Parsing (Bandit B405)
**File:** src/report_generator.py:18  
**Status:** ✅ SAFE - Using ElementTree for SVG manipulation, not untrusted XML

#### JavaScript False Positive (Bandit B608)
**File:** src/visualizer.py:687  
**Status:** ✅ FALSE POSITIVE - JavaScript code, not SQL

## Monitoring

### pygments CVE-2026-4539
**Status:** No fix available yet  
**Impact:** LOW - Requires local access and specific lexer  
**Action:** Monitor for security release

## Remediation Plan

### Phase 1: Immediate (P1-high)
- [ ] Upgrade requests to >=2.33.0
- [ ] Upgrade tornado to >=6.5.5
- [ ] Update requirements.txt
- [ ] Test application functionality
- [ ] Run pip-audit to verify

### Phase 2: Short-term (P2-medium)
- [ ] Replace MD5 with SHA256 in cache keys
- [ ] Clear existing caches (keys will change)
- [ ] Verify caching still works

### Phase 3: Code Quality (P3-low)
- [ ] Improve exception handling (5 locations)
- [ ] Add specific exception types
- [ ] Add logging for debugging

## Verification

After remediation:
```bash
# Run security scans
bandit -r src/ main.py
pip-audit

# Expected results:
# - Bandit: 0 HIGH/MEDIUM issues (only false positives)
# - pip-audit: 0-1 vulnerabilities (pygments if not fixed)
```

## GitHub Issues Created

- **#60** - Security: Upgrade vulnerable dependencies (P1-high)
- **#59** - Security: Replace MD5 hash with SHA256 (P2-medium)
- **#61** - Code Quality: Improve exception handling (P3-low)

## Compliance

### OWASP Top 10 2021
- ✅ **A01:2021 – Broken Access Control** - Not applicable
- ✅ **A02:2021 – Cryptographic Failures** - Addressed in #59
- ✅ **A03:2021 – Injection** - No vulnerabilities found
- ✅ **A06:2021 – Vulnerable Components** - Addressed in #60

### CWE Top 25
- ✅ **CWE-327** - Weak Crypto - Addressed in #59
- ✅ **CWE-703** - Improper Check - Addressed in #61

## Scan Artifacts

- `security_scan_bandit.json` - Full Bandit report
- `security_scan_pip_audit.json` - Full pip-audit report

---

**Next Scan:** 2026-04-26 (Monthly)  
**Scan Frequency:** Monthly or after major dependency updates