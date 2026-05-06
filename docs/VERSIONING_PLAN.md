# Versioning Plan: CLI to Web Platform Migration

**Date:** 2026-05-06  
**Purpose:** Restate project versioning to reflect architectural shift from CLI tool to web platform

---

## Overview

The Ride Optimizer project is transitioning from a command-line desktop application to a web-based platform. To reflect this significant architectural change, we are restating all previous releases as pre-1.0 versions (0.x.x) and designating the web platform launch as **version 1.0.0**.

---

## Rationale

### Why Reversion to 0.x.x?

The current CLI-based system, while feature-complete and production-ready for its intended use case, represents a **prototype/beta phase** of the broader vision:

1. **Limited Accessibility** - Requires command-line knowledge and manual execution
2. **Single-Use Pattern** - Generate report, view in browser, repeat
3. **No Persistence** - Each analysis is independent, no historical tracking
4. **Manual Scheduling** - User must remember to run analysis
5. **Desktop-Only** - Not accessible from mobile or other devices

### Why 1.0.0 for Web Platform?

Version 1.0.0 represents the **first production-ready, user-facing platform** with:

1. **Web Interface** - Accessible from any device with a browser
2. **Automated Operation** - Scheduled analysis runs without user intervention
3. **Persistent State** - Database-backed historical tracking
4. **Always Available** - Server running 24/7 on Raspberry Pi
5. **Mobile-Friendly** - Responsive design for laptop and mobile access

This is the **first version suitable for daily, non-technical use** - a true 1.0 milestone.

---

## Version Mapping

### Current Versions → Restated Versions

| Original Version | Restated Version | Release Date | Notes |
|-----------------|------------------|--------------|-------|
| v2.4.0 | **v0.5.0** | 2026-03-30 | Long Rides Feature & Polish |
| v2.3.0 | **v0.4.0** | 2026-03-27 | Segment-Based Route Naming |
| v2.2.0 | **v0.3.0** | 2026-03-27 | Test Infrastructure |
| v2.1.0 | **v0.2.0** | 2026-03-26 | Performance Improvements |
| v2.0.0 | **v0.1.0** | Earlier | Initial Release |

### Rationale for 0.x Numbering

- **0.1.0** - Initial working prototype
- **0.2.0** - Performance and naming improvements
- **0.3.0** - Testing infrastructure (quality milestone)
- **0.4.0** - Security and naming enhancements
- **0.5.0** - Feature completeness for CLI (long rides, mobile optimization)

Each 0.x version represents incremental improvements to the CLI prototype, building toward the 1.0 web platform vision.

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