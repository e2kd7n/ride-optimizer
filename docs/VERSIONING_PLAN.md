# Versioning Plan: Pre-1.0 Development

**Date:** 2026-05-06
**Updated:** 2026-05-07 (Version Rebaseline - Corrected)
**Purpose:** All releases are 0.x.x until production-ready 1.0.0

---

## Overview

The Ride Optimizer uses 0.x.x versioning for all pre-production development. Version 1.0.0 is reserved for the first truly production-ready release.

---

## Complete Version History

### Original Prototype

| Version | Status | Architecture | Notes |
|---------|--------|--------------|-------|
| v0.5.0 | Original | CLI + Static HTML | Simple, lightweight prototype |

### Flask Experiment (Renumbered from v2.x)

| Old Number | New Number | Release Date | Status | Architecture | Notes |
|------------|------------|--------------|--------|--------------|-------|
| v2.1.0 | **v0.6.0** | 2026-03-26 | Released | Flask + SQLAlchemy | Code quality & design system |
| v2.2.0 | **v0.7.0** | 2026-03-30 | Released | + Test Infrastructure | Test infrastructure added |
| v2.3.0 | **v0.8.0** | 2026-03-30 | Released | + Route Naming | Segment-based route naming |
| v2.4.0 | **v0.9.0** | 2026-03-30 | Released | + Long Rides | Long rides feature & polish |
| v2.5.0 | **v0.10.0** | 2026-03-30 | Current | + APScheduler + Docker | Current release (over-engineered) |

### Planned Releases (Leaving Headroom for 1.0.0)

| Version | Target Date | Status | Architecture | Notes |
|---------|-------------|--------|--------------|-------|
| v0.11.0 | 2026-06 (5 weeks) | Planned | Simplified (Static + API) | Architecture simplification (Issue #152) |
| v0.12.0 | TBD | Future | + Refinements | Bug fixes and polish |
| v0.13.0 | TBD | Future | + Features | Additional features as needed |
| ... | TBD | Future | ... | Plenty of headroom |
| v0.99.0 | TBD | Future | Beta | Final pre-production testing |
| **v1.0.0** | TBD | **Future** | **Production Ready** | **First stable production release** |

---

## Why 0.x.x Versioning?

**Semantic Versioning Convention:**
- **0.x.x** = Pre-production, API may change, not production-ready
- **1.0.0** = First stable, production-ready release
- **1.x.x** = Stable, backward-compatible improvements
- **2.0.0** = Major breaking changes

**Current Status:**
- Still refining architecture (Issue #152)
- Not yet battle-tested in daily use
- API and features may still change
- Honest about maturity level

**When to Release 1.0.0:**
- Architecture proven stable on Raspberry Pi
- Used successfully in daily production for 3+ months
- All core features complete and tested
- Documentation comprehensive
- No major known issues
- Confident in long-term API stability

---

## Version Renumbering Plan

### GitHub Release Tags (Need to Retag)

```bash
# Delete old v2.x tags
git tag -d v2.1.0 v2.2.0 v2.3.0 v2.4.0 v2.5.0
git push origin :refs/tags/v2.1.0 :refs/tags/v2.2.0 :refs/tags/v2.3.0 :refs/tags/v2.4.0 :refs/tags/v2.5.0

# Create new v0.x tags at same commits
git tag v0.6.0 <commit-hash-of-v2.1.0>
git tag v0.7.0 <commit-hash-of-v2.2.0>
git tag v0.8.0 <commit-hash-of-v2.3.0>
git tag v0.9.0 <commit-hash-of-v2.4.0>
git tag v0.10.0 <commit-hash-of-v2.5.0>

# Push new tags
git push origin v0.6.0 v0.7.0 v0.8.0 v0.9.0 v0.10.0
```

### Documentation Updates

All references to v2.x.0 versions should be updated to v0.x.0:
- v2.1.0 → v0.6.0
- v2.2.0 → v0.7.0
- v2.3.0 → v0.8.0
- v2.4.0 → v0.9.0
- v2.5.0 → v0.10.0

---

## Summary

- **v0.5.0** = Original CLI + static HTML prototype
- **v0.6.0-v0.10.0** = Flask experiment (formerly v2.1.0-v2.5.0)
- **v0.11.0** = Next release (simplified architecture)
- **v0.12.0-v0.99.0** = Headroom for future development
- **v1.0.0** = Production-ready release (when truly ready)

This numbering scheme is honest about the project's maturity and leaves plenty of room for development before declaring production readiness.

---

## Why Reset to v1.0.0?

### Problems with v2.5.0 Architecture

The current v2.5.0 release, while functional, is **over-engineered for single-user deployment**:

1. **Resource Bloat** - 250-300MB memory usage (Flask + SQLAlchemy + APScheduler)
2. **Complexity** - 27 dependencies, Docker containerization, ORM abstraction
3. **Multi-User Infrastructure** - Unnecessary for personal tool
4. **Slow Startup** - 5-8 seconds to initialize Flask app
5. **Maintenance Burden** - Complex stack for simple use case

### Why v1.0.0 Represents Production Ready

Version 1.0.0 will be the **first truly production-ready release** because:

1. **Optimized for Target Use Case** - Single-user Raspberry Pi deployment
2. **Minimal Resource Usage** - 50MB memory (80% reduction)
3. **Simplified Architecture** - 12 dependencies, no Docker, no ORM
4. **Fast Startup** - <1 second (static files)
5. **Easy Maintenance** - Pragmatic, minimal solutions
6. **100% Feature Preservation** - All v2.5.0 features retained

**Semantic Versioning Justification:**
v1.0.0 signals "production ready" better than v2.6.0 or v3.0.0. The architecture change is significant enough to warrant a major version reset, and v1.0.0 clearly communicates "first stable release."

---

## Deprecated Version References

The following version numbers appeared in documentation but **never existed as GitHub releases**:

| Version | Status | Reason |
|---------|--------|--------|
| v0.9.0 | Never Released | Documentation artifact, superseded by v2.5.0 |
| v0.9.1 | Never Released | Planned but deprecated, merged into v1.0.0 |
| v0.9.2 | Never Released | Planned but deprecated, merged into v1.0.0 |
| v0.9.3 | Never Released | Planned but deprecated, merged into v1.0.0 |
| v3.0.0 | Never Released | Version number confusion, replaced by v1.0.0 |

**Note:** These versions were planning artifacts that don't align with actual release history.

---

## Version 1.0.0 Milestone

### Target: Web Platform Launch

**Version:** 1.0.0  
**Codename:** "Web Platform"  
**Target Date:** Q3 2026 (8-10 weeks from proposal approval)

### Core Features (1.0.0)

#### Must-Have (Blocking 1.0 Release)
- ✅ Web-based dashboard accessible via browser
- ✅ Automated daily analysis (3am scheduled runs)
- ✅ Commute recommendations view (today's optimal routes)
- ✅ Long ride route planner (form-based interface)
- ✅ SQLite database for persistent state
- ✅ Mobile-responsive design
- ✅ Raspberry Pi deployment with Podman
- ✅ Systemd service management

#### Nice-to-Have (Can defer to 1.1.0)
- Route library browser
- Historical trend analysis
- Advanced settings UI
- Export functionality
- PWA (Progressive Web App) support

### Success Criteria for 1.0.0

1. **Functionality**
   - User can access dashboard from laptop and mobile
   - Daily analysis runs automatically at 3am
   - Commute recommendations display correctly
   - Long ride planner generates valid routes
   - No command-line interaction required for normal use

2. **Performance**
   - Page loads in <2 seconds on local network
   - Analysis completes in <5 minutes
   - Raspberry Pi temperature stays <70°C
   - Memory usage <1GB

3. **Reliability**
   - 99% uptime over 30 days
   - Scheduled jobs run successfully
   - No data loss or corruption
   - Graceful error handling

4. **Usability**
   - Intuitive interface (no manual needed)
   - Mobile experience smooth
   - Fast enough for interactive use
   - Clear error messages

---

## Migration Path

### Phase 1: Preparation (Week 1)
- Archive current CLI codebase as v0.5.0
- Create new branch: `feature/web-platform-1.0`
- Set up Flask application structure
- Update documentation with new versioning

### Phase 2: Development (Weeks 2-7)
- Implement web interface (Phases 1-3 from proposal)
- Maintain backward compatibility with CLI
- Run both systems in parallel during development
- Continuous testing on Raspberry Pi

### Phase 3: Beta Testing (Week 8)
- Deploy to Raspberry Pi for real-world testing
- Use web interface for daily commute decisions
- Gather feedback and fix issues
- Performance tuning

### Phase 4: Release (Week 9-10)
- Final testing and bug fixes
- Update all documentation
- Create release notes for v1.0.0
- Tag release and deploy to production

### Phase 5: Deprecation (Post-1.0)
- CLI remains available but deprecated
- Focus all new features on web platform
- CLI may be removed in v2.0.0

---

## Future Versioning Strategy

### Semantic Versioning (SemVer)

Following standard semantic versioning: `MAJOR.MINOR.PATCH`

**MAJOR** (1.x.x → 2.x.x)
- Breaking changes to API or data format
- Major architectural changes
- Example: Multi-user support, cloud migration

**MINOR** (1.0.x → 1.1.x)
- New features (backward compatible)
- Example: Route library, PWA support, notifications

**PATCH** (1.0.0 → 1.0.1)
- Bug fixes
- Performance improvements
- Security patches

### Planned Roadmap

**v1.0.0** (Q3 2026) - Web Platform Launch
- Core web interface
- Automated analysis
- Commute recommendations
- Long ride planner

**v1.1.0** (Q4 2026) - Enhanced Features
- Route library browser
- Historical trend analysis
- Advanced settings UI
- Export functionality

**v1.2.0** (Q1 2027) - Mobile Optimization
- PWA support
- Offline mode
- Push notifications
- Mobile app shortcuts

**v1.3.0** (Q2 2027) - Intelligence
- Machine learning route predictions
- Weather pattern analysis
- Training plan suggestions
- Performance insights

**v2.0.0** (Q3 2027+) - Multi-User Platform
- User authentication
- Multiple user support
- Cloud deployment option
- API for third-party integrations

---

## Communication Plan

### Documentation Updates

1. **README.md**
   - Update version history section
   - Add note about versioning change
   - Link to this document

2. **Release Notes**
   - Create v0.5.0 release notes (restated from v2.4.0)
   - Archive old release notes with version mapping
   - Prepare v1.0.0 release notes template

3. **Technical Spec**
   - Update version references
   - Add web platform architecture
   - Document migration path

### Git Tags

```bash
# Retag existing releases with 0.x versions
git tag v0.1.0 <commit-hash-of-v2.0.0>
git tag v0.2.0 <commit-hash-of-v2.1.0>
git tag v0.3.0 <commit-hash-of-v2.2.0>
git tag v0.4.0 <commit-hash-of-v2.3.0>
git tag v0.5.0 <commit-hash-of-v2.4.0>

# Keep old tags for reference (mark as deprecated)
git tag v2.4.0-deprecated <commit-hash-of-v2.4.0>

# Push new tags
git push origin --tags
```

### Changelog

Create `CHANGELOG.md` following Keep a Changelog format:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Web-based dashboard interface
- Automated daily analysis scheduling
- Long ride route planner

## [0.5.0] - 2026-03-30 (formerly v2.4.0)

### Added
- Long rides analysis feature
- Mobile optimizations
- Form validation
- GPU-accelerated animations

## [0.4.0] - 2026-03-27 (formerly v2.3.0)

### Added
- Intelligent route naming with segments
- SHA256 migration for security

...
```

---

## Benefits of This Approach

### For Users
1. **Clear Expectations** - 1.0.0 signals "production ready for daily use"
2. **Honest Versioning** - 0.x reflects CLI's prototype nature
3. **Excitement** - 1.0 launch is a milestone worth celebrating

### For Development
1. **Clean Slate** - Fresh start for web platform
2. **Flexibility** - Can make breaking changes before 1.0
3. **Roadmap Clarity** - Easy to communicate future versions

### For Project
1. **Professional** - Follows industry standards
2. **Sustainable** - Clear versioning strategy for future
3. **Marketable** - "Version 1.0 Launch" is a story

---

## Risks and Mitigation

### Risk: User Confusion
**Mitigation:**
- Clear communication in release notes
- Version mapping table in documentation
- Deprecation notices in CLI

### Risk: Breaking Changes
**Mitigation:**
- Maintain CLI backward compatibility
- Gradual migration path
- Clear upgrade guide

### Risk: Delayed 1.0 Launch
**Mitigation:**
- Realistic timeline (8-10 weeks)
- MVP approach (defer nice-to-haves)
- Regular progress updates

---

## Approval and Next Steps

### Required Approvals
- [x] Project owner review
- [ ] Technical review
- [ ] Documentation review

### Immediate Actions (Upon Approval)
1. Update README.md with version mapping
2. Create CHANGELOG.md
3. Retag Git releases
4. Update proposal with 1.0.0 milestone
5. Begin Phase 1 development

---

**Prepared By:** Senior Development Team  
**Date:** 2026-05-06  
**Status:** Ready for Review