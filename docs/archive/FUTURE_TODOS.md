tc# Future TODO Items

## Route Matching Issues
- **GitHub Issue**: [#123](https://github.com/e2kd7n/ride-optimizer/issues/123)
- **TODO**: Examine why routes 78 and 62 aren't matching
  - Need to investigate route similarity algorithm
  - Check if these routes should be grouped together
  - Review distance/coordinate comparison thresholds

## Map UI/UX Improvements
- **GitHub Issue**: [#124](https://github.com/e2kd7n/ride-optimizer/issues/124)
- **TODO**: Ensure polylines and tooltips selected are on top of all subdued lines
  - Selected routes should have higher z-index
  - Tooltips should appear above all map elements
  - Improve visual hierarchy for selected vs. non-selected routes

## Progress Bar Display Issue - RESOLVED
- **COMPLETED** (2026-03-27): Improved progress bar display with step counts
  - **Solution Implemented**:
    - Changed bar_format to show step counts: `{n}/{total} |{bar}| {percentage:3.0f}%`
    - This provides clear indication of which step is running (e.g., "2/8 steps")
    - Maintains clean phase transitions with `print()` after each step
    - Minimal overhead - no nested progress bars or callbacks needed
  - **Decision**: Avoided nested progress bars due to performance concerns
    - Nested bars with callbacks would add overhead to each operation
    - Current solution provides sufficient progress visibility
    - Individual module progress (e.g., "Loading activities: 45/100") would require:
      * Passing callbacks through multiple layers
      * Frequent progress updates during tight loops
      * Potential 5-10% performance impact
    - If detailed progress is needed in future, implement with `--verbose` flag
  - **Related Change**: Added user prompt for background geocoding
    - Users now approve before geocoding terminal window opens
    - Provides clear explanation of what will happen
    - Can decline if not needed

---

*These items are tracked separately from issue #58 implementation*
*Created: 2026-03-27*