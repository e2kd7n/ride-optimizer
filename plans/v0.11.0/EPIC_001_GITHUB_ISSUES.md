# EPIC-001 GitHub Issues Summary

**Created:** 2026-05-07  
**Epic Document:** [`INTERACTIVE_MAPS_RESTORATION_EPIC.md`](INTERACTIVE_MAPS_RESTORATION_EPIC.md)

---

## Epic Issue

**#235** - [EPIC-001] Restore Interactive Maps to Web App  
- **Priority:** P0-critical  
- **Labels:** epic, P0-critical  
- **URL:** https://github.com/e2kd7n/ride-optimizer/issues/235

---

## Child Story Issues

### Phase 1: Core Maps (P0-critical)

**#228** - [EPIC-001] Add interactive map to route detail page  
- **Priority:** P0-critical  
- **Estimate:** 3 days  
- **Dependencies:** None  
- **Labels:** P0-critical, enhancement  
- **URL:** https://github.com/e2kd7n/ride-optimizer/issues/228

**#229** - [EPIC-001] Add route comparison map to commute page  
- **Priority:** P0-critical  
- **Estimate:** 5 days  
- **Dependencies:** #228  
- **Labels:** P0-critical, enhancement  
- **URL:** https://github.com/e2kd7n/ride-optimizer/issues/229

### Phase 2: Extended Maps (P1-high)

**#230** - [EPIC-001] Add long ride visualization map to planner page  
- **Priority:** P1-high  
- **Estimate:** 5 days  
- **Dependencies:** #228, #229  
- **Labels:** P1-high, enhancement  
- **URL:** https://github.com/e2kd7n/ride-optimizer/issues/230

**#231** - [EPIC-001] Add overview map to dashboard  
- **Priority:** P1-high  
- **Estimate:** 4 days  
- **Dependencies:** #229  
- **Labels:** P1-high, enhancement  
- **URL:** https://github.com/e2kd7n/ride-optimizer/issues/231

### Phase 3: Enhanced Features (P2-medium)

**#232** - [EPIC-001] Add interactive map filtering and route selection  
- **Priority:** P2-medium  
- **Estimate:** 3 days  
- **Dependencies:** #228, #229, #230, #231  
- **Labels:** P2-medium, enhancement  
- **URL:** https://github.com/e2kd7n/ride-optimizer/issues/232

**#233** - [EPIC-001] Add weather overlays to maps  
- **Priority:** P2-medium  
- **Estimate:** 3 days  
- **Dependencies:** #229  
- **Labels:** P2-medium, enhancement  
- **URL:** https://github.com/e2kd7n/ride-optimizer/issues/233

### Phase 4: Advanced Features (P3-low)

**#234** - [EPIC-001] Add advanced map features (elevation, analytics)  
- **Priority:** P3-low  
- **Estimate:** 5 days  
- **Dependencies:** #228, #229, #230, #231, #232, #233  
- **Labels:** P3-low, enhancement  
- **URL:** https://github.com/e2kd7n/ride-optimizer/issues/234

---

## Quick Reference Table

| Issue | Title | Priority | Estimate | Dependencies |
|-------|-------|----------|----------|--------------|
| #235 | **EPIC: Restore Interactive Maps** | P0-critical | 28 days | - |
| #228 | Route detail page maps | P0-critical | 3 days | None |
| #229 | Commute page maps | P0-critical | 5 days | #228 |
| #230 | Planner page maps | P1-high | 5 days | #228, #229 |
| #231 | Dashboard overview map | P1-high | 4 days | #229 |
| #232 | Interactive features | P2-medium | 3 days | #228-231 |
| #233 | Weather overlays | P2-medium | 3 days | #229 |
| #234 | Advanced features | P3-low | 5 days | #228-233 |

---

## Implementation Order

### Sprint 1 (Week 1-2) - Core Maps
1. Start with #228 (Route detail) - 3 days
2. Then #229 (Commute page) - 5 days
3. **Deliverable:** Maps on route detail and commute pages

### Sprint 2 (Week 3-4) - Extended Maps
1. Start #230 (Planner page) - 5 days
2. Parallel with #231 (Dashboard) - 4 days
3. **Deliverable:** Maps on all major pages

### Sprint 3 (Week 5-6) - Enhanced Features
1. Add #232 (Interactive features) - 3 days
2. Add #233 (Weather overlays) - 3 days
3. **Deliverable:** Full interactivity and weather integration

### Sprint 4 (Week 7-8) - Advanced Features (Optional)
1. Implement #234 (Advanced features) - 5 days
2. **Deliverable:** Elevation profiles, analytics, export

---

## Total Effort

- **Total Story Points:** 28 days (5.6 weeks)
- **Critical Path:** #228 → #229 → #230 → #232 → #234
- **Parallel Work Possible:** #231 can run parallel with #230
- **Minimum Viable:** #228 + #229 (8 days, 1.6 weeks)

---

## Related Documentation

- Epic Document: [`plans/v0.11.0/INTERACTIVE_MAPS_RESTORATION_EPIC.md`](INTERACTIVE_MAPS_RESTORATION_EPIC.md)
- Existing Code: [`src/visualizer.py`](../../src/visualizer.py) (1316 lines)
- Related Issue: #169 - "Coming Soon" placeholder on route detail page

---

## Commands to View Issues

```bash
# View epic
gh issue view 235

# View all story issues
gh issue list --label "enhancement" --search "EPIC-001"

# View by priority
gh issue list --label "P0-critical" --search "EPIC-001"
gh issue list --label "P1-high" --search "EPIC-001"
gh issue list --label "P2-medium" --search "EPIC-001"
gh issue list --label "P3-low" --search "EPIC-001"
```

---

**Last Updated:** 2026-05-07