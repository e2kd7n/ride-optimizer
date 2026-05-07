# Documentation

This directory contains all documentation for the Ride Optimizer application, organized by category.

---

## 📁 Directory Structure

### [`/releases/`](releases/)
Release documentation organized by version, including:
- Release notes for each version
- Time tracking reports
- Feature implementation summaries
- Historical release information

**Quick Links:**
- [Release Documentation Index](releases/README.md)
- [Historical Releases](releases/HISTORICAL_RELEASES.md)
- [Time Tracking Summary](releases/TIME_TRACKING.md)

### [`/guides/`](guides/)
User guides and implementation documentation, including:
- Authentication and security setup
- Feature-specific guides (mobile, weather, parallelism)
- Implementation best practices

**Quick Links:**
- [Guides Index](guides/README.md)
- [Authentication Guide](guides/AUTHENTICATION_GUIDE.md)
- [Mobile Usage Guide](guides/MOBILE_USAGE_GUIDE.md)
- [Weather Guide](guides/WEATHER_GUIDE.md)

### [`/archive/`](archive/)
Archived documentation for historical reference, including:
- Completed code reviews and audits
- Security documentation and fixes
- Superseded documentation

**Quick Links:**
- [Archive Index](archive/README.md)

---

## 📚 Core Documentation

### Root-Level Documents
- [`TECHNICAL_SPEC.md`](TECHNICAL_SPEC.md) - Complete technical specification
- [`FUTURE_TODOS.md`](FUTURE_TODOS.md) - Planned features and improvements
- [`TEST_COVERAGE_ROADMAP.md`](TEST_COVERAGE_ROADMAP.md) - Test coverage roadmap and strategy
- [`VERSION_REBASELINE_PLAN.md`](VERSION_REBASELINE_PLAN.md) - Version rebaseline plan

---

## 🔍 Finding Documentation

### By Topic

**Getting Started:**
- [Project README](../README.md)
- [Implementation Guide](guides/IMPLEMENTATION_GUIDE.md)
- [Authentication Guide](guides/AUTHENTICATION_GUIDE.md)

**Features:**
- [Mobile Usage](guides/MOBILE_USAGE_GUIDE.md)
- [Weather Integration](guides/WEATHER_GUIDE.md)
- [Next Commute](releases/v0.8.0/NEXT_COMMUTE_FEATURE.md)
- [Long Rides](releases/v0.9.0/LONG_RIDES_IMPLEMENTATION_SUMMARY.md)

**Performance:**
- [Parallelism Guide](guides/PARALLELISM_GUIDE.md)

**Releases:**
- [All Releases](releases/HISTORICAL_RELEASES.md)
- [Latest Release Notes](releases/)

**Planning:**
- [Future TODOs](FUTURE_TODOS.md)
- [Technical Specification](TECHNICAL_SPEC.md)

### By Version
- **v2.0.0:** [Release Notes](releases/v2.0.0/RELEASE_NOTES.md)
- **v0.6.0:** [Release Notes](releases/v0.6.0/RELEASE_NOTES_v0.6.0.md)
- **v0.7.0:** [Features](releases/v0.7.0/)
- **v0.8.0:** [Next Commute](releases/v0.8.0/NEXT_COMMUTE_FEATURE.md)
- **v0.9.0:** [Long Rides](releases/v0.9.0/LONG_RIDES_IMPLEMENTATION_SUMMARY.md)
- **v0.10.0:** [Background Geocoding](releases/v0.10.0/BACKGROUND_GEOCODING_IMPLEMENTATION.md)

---

## 📝 Documentation Standards

### File Naming
- Use `SCREAMING_SNAKE_CASE.md` for documentation files
- End guide files with `_GUIDE.md`
- End feature documentation with `_FEATURE.md` or `_IMPLEMENTATION_SUMMARY.md`
- Use `README.md` for directory indexes

### Organization
- **Releases:** Version-specific documentation goes in `releases/vX.Y.Z/`
- **Guides:** User-facing guides go in `guides/`
- **Archive:** Completed/superseded docs go in `archive/`
- **Root:** Core technical specs and planning docs stay at `docs/` root

### Content Guidelines
- Include a table of contents for documents longer than 3 sections
- Use clear, descriptive headings
- Link to related documentation
- Keep documents focused on a single topic
- Update the relevant README when adding new documents

---

## 🔗 External Documentation

- **Project Root:** [`../README.md`](../README.md)
- **Issue Tracking:** [`../ISSUE_PRIORITIES.md`](../ISSUE_PRIORITIES.md), [`../ISSUES_TRACKING.md`](../ISSUES_TRACKING.md)
- **Plans:** [`../plans/`](../plans/)
- **Scripts:** [`../scripts/README.md`](../scripts/README.md)

---

## 🤝 Contributing

When adding new documentation:
1. Choose the appropriate directory (`releases/`, `guides/`, or `archive/`)
2. Follow the naming conventions above
3. Update the relevant README file
4. Link to related documentation
5. Keep the document focused and well-organized

---

**Last Updated:** May 5, 2026  
**Maintained By:** Development Team  
**Repository:** ride-optimizer