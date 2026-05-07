# Versioning Plan: Architecture Simplification

**Date:** 2026-05-06
**Updated:** 2026-05-07 (Version Rebaseline)
**Purpose:** Document version scheme and transition to v1.0.0 production release

---

## Overview

The Ride Optimizer project is transitioning from v2.5.0 (pre-production) to v1.0.0 (first production-ready release). This version reset reflects a significant architectural simplification optimized for single-user Raspberry Pi deployment.

---

## Current Version Scheme

### Active Releases (GitHub)

| Version | Release Date | Status | Notes |
|---------|--------------|--------|-------|
| v2.5.0 | 2026-03-30 | Current | Last pre-production release |
| v2.4.0 | 2026-03-30 | Released | Long rides feature & polish |
| v2.3.0 | 2026-03-30 | Released | Segment-based route naming |
| v2.2.0 | 2026-03-30 | Released | Test infrastructure |
| v2.1.0 | 2026-03-26 | Released | Code quality & design system |

### Next Release

| Version | Target Date | Status | Notes |
|---------|-------------|--------|-------|
| v1.0.0 | 2026-06 (5 weeks) | In Planning | First production-ready release with simplified architecture |

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