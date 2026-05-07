#!/usr/bin/env python3
"""
Create GitHub issues from triaged todos.

This script creates GitHub issues using the GitHub CLI for prioritized todo items.
It supports dry-run mode and includes proper error handling.
"""

import subprocess
import sys
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class Issue:
    """Represents a GitHub issue to be created."""
    title: str
    priority: str
    labels: List[str]
    body: str = ""


def get_issues() -> List[Issue]:
    """Define all issues to be created with their metadata."""
    issues = []
    
    # P1-high issues (8 items)
    p1_issues = [
        Issue(
            title="Build planner frontend UI (currently placeholder only)",
            priority="P1-high",
            labels=["P1-high", "enhancement", "ux", "frontend"],
            body="The planner page currently shows only a placeholder. Need to implement the full frontend UI for the ride planner feature.\n\n**Acceptance Criteria:**\n- Replace placeholder with functional planner interface\n- Integrate with planner API endpoints\n- Follow mobile-first design principles\n- Ensure WCAG AA accessibility compliance"
        ),
        Issue(
            title="Add Marshmallow validation schemas for planner endpoints",
            priority="P1-high",
            labels=["P1-high", "enhancement", "backend"],
            body="Planner API endpoints need proper request/response validation using Marshmallow schemas.\n\n**Acceptance Criteria:**\n- Create validation schemas for all planner endpoints\n- Add input validation for date ranges, preferences, etc.\n- Include proper error messages for validation failures\n- Add tests for validation edge cases"
        ),
        Issue(
            title="UI/UX: Fix page counter display",
            priority="P1-high",
            labels=["P1-high", "bug", "ux"],
            body="Page counter display issue identified in QA.\n\n**Reference:** Issue #6\n\n**Acceptance Criteria:**\n- Fix page counter display logic\n- Ensure correct pagination state\n- Test with various data set sizes"
        ),
        Issue(
            title="UI/UX: Fix route name display",
            priority="P1-high",
            labels=["P1-high", "bug", "ux"],
            body="Route name display issue identified in QA.\n\n**Reference:** Issue #2\n\n**Acceptance Criteria:**\n- Fix route name rendering\n- Ensure proper truncation for long names\n- Test with various route name formats"
        ),
        Issue(
            title="UI/UX: Simplify route counter",
            priority="P1-high",
            labels=["P1-high", "enhancement", "ux"],
            body="Route counter needs simplification for better UX.\n\n**Reference:** Issue #7\n\n**Acceptance Criteria:**\n- Simplify counter display logic\n- Improve readability\n- Ensure mobile-friendly layout"
        ),
        Issue(
            title="UI/UX: Add table sorting functionality",
            priority="P1-high",
            labels=["P1-high", "enhancement", "ux"],
            body="Add sorting capability to route tables.\n\n**Reference:** Issue #1\n\n**Acceptance Criteria:**\n- Implement column sorting (ascending/descending)\n- Add visual indicators for sort state\n- Persist sort preferences\n- Ensure keyboard accessibility"
        ),
        Issue(
            title="UI/UX: Update polyline colors",
            priority="P1-high",
            labels=["P1-high", "enhancement", "ux", "design"],
            body="Update polyline colors to match semantic color system.\n\n**Reference:** Issue #3\n\n**Acceptance Criteria:**\n- Use semantic colors (green=optimal, red=danger, yellow=caution, blue=info)\n- Ensure WCAG AA contrast compliance\n- Update documentation with color meanings"
        ),
        Issue(
            title="UI/UX: Add clickable 'Uses' column with modal",
            priority="P1-high",
            labels=["P1-high", "enhancement", "ux"],
            body="Make 'Uses' column clickable to show detailed activity list in modal.\n\n**Reference:** Issue #5\n\n**Acceptance Criteria:**\n- Add click handler to Uses column\n- Create modal component for activity details\n- Show activity date, time, conditions\n- Ensure keyboard and screen reader accessibility"
        ),
    ]
    issues.extend(p1_issues)
    
    # P2-medium issues (17 items)
    p2_issues = [
        Issue(
            title="Implement log rotation with RotatingFileHandler",
            priority="P2-medium",
            labels=["P2-medium", "enhancement", "backend"],
            body="Add log rotation to prevent unbounded log file growth.\n\n**Acceptance Criteria:**\n- Implement RotatingFileHandler for all loggers\n- Set reasonable size limits (e.g., 10MB per file)\n- Keep 5 backup files\n- Test rotation behavior"
        ),
        Issue(
            title="Add PII sanitization to logging",
            priority="P2-medium",
            labels=["P2-medium", "security", "backend"],
            body="Ensure no PII (personally identifiable information) is logged.\n\n**Acceptance Criteria:**\n- Audit all log statements for PII\n- Add sanitization for user data, tokens, coordinates\n- Create logging utility functions for safe logging\n- Document PII handling policy"
        ),
        Issue(
            title="Add planner-specific API client methods",
            priority="P2-medium",
            labels=["P2-medium", "enhancement", "backend"],
            body="Add planner-specific methods to API client (getLongRideRecommendations, etc).\n\n**Acceptance Criteria:**\n- Add getLongRideRecommendations() method\n- Add other planner-specific endpoints\n- Include proper error handling\n- Add JSDoc documentation"
        ),
        Issue(
            title="Create PRIVACY.md policy for compliance",
            priority="P2-medium",
            labels=["P2-medium", "documentation", "security"],
            body="Create comprehensive privacy policy document.\n\n**Acceptance Criteria:**\n- Document data collection practices\n- Explain data storage and encryption\n- Detail data retention policies\n- Include user rights and contact information"
        ),
        Issue(
            title="Code Quality: Replace 4 bare except statements with specific exceptions",
            priority="P2-medium",
            labels=["P2-medium", "enhancement"],
            body="Replace bare `except:` statements with specific exception types.\n\n**Acceptance Criteria:**\n- Identify all 4 bare except statements\n- Replace with specific exception types\n- Add appropriate error handling\n- Ensure no functionality regression"
        ),
        Issue(
            title="Code Quality: Add debug logging for exception handlers",
            priority="P2-medium",
            labels=["P2-medium", "enhancement", "backend"],
            body="Add debug-level logging to all exception handlers for better troubleshooting.\n\n**Acceptance Criteria:**\n- Add debug logs to all try/except blocks\n- Include exception type and message\n- Log relevant context (function name, parameters)\n- Test logging output"
        ),
        Issue(
            title="Testing: Increase Long Ride Analyzer coverage 13% → 50%",
            priority="P2-medium",
            labels=["P2-medium", "testing"],
            body="Increase test coverage for Long Ride Analyzer from 13% to 50%.\n\n**Current Coverage:** 13%\n**Target Coverage:** 50%\n\n**Acceptance Criteria:**\n- Add unit tests for core analysis logic\n- Test edge cases and error conditions\n- Achieve 50% line coverage\n- All tests must pass"
        ),
        Issue(
            title="Testing: Increase Data Fetcher coverage 49% → 80%",
            priority="P2-medium",
            labels=["P2-medium", "testing"],
            body="Increase test coverage for Data Fetcher from 49% to 80%.\n\n**Current Coverage:** 49%\n**Target Coverage:** 80%\n\n**Acceptance Criteria:**\n- Add tests for API interactions\n- Mock external dependencies\n- Test error handling and retries\n- Achieve 80% line coverage"
        ),
        Issue(
            title="Testing: Increase Route Analyzer coverage 20% → 50%",
            priority="P2-medium",
            labels=["P2-medium", "testing"],
            body="Increase test coverage for Route Analyzer from 20% to 50%.\n\n**Current Coverage:** 20%\n**Target Coverage:** 50%\n\n**Acceptance Criteria:**\n- Add tests for route similarity algorithms\n- Test Fréchet and Hausdorff distance calculations\n- Test route grouping logic\n- Achieve 50% line coverage"
        ),
        Issue(
            title="Testing: Increase Route Namer coverage 15% → 50%",
            priority="P2-medium",
            labels=["P2-medium", "testing"],
            body="Increase test coverage for Route Namer from 15% to 50%.\n\n**Current Coverage:** 15%\n**Target Coverage:** 50%\n\n**Acceptance Criteria:**\n- Add tests for naming algorithms\n- Test segment-based naming\n- Test edge cases (short routes, loops)\n- Achieve 50% line coverage"
        ),
        Issue(
            title="Verify GitHub issues #138, #139, #140 status",
            priority="P2-medium",
            labels=["P2-medium", "question"],
            body="Verify completion status of weather, TrainerRoad, and workout-aware issues.\n\n**Issues to Check:**\n- #138: Weather integration\n- #139: TrainerRoad integration\n- #140: Workout-aware logic\n\n**Acceptance Criteria:**\n- Check if issues are closed\n- Verify implementation is complete\n- Test functionality if implemented\n- Create follow-up issues if incomplete"
        ),
        Issue(
            title="Implement actual weather integration if #138 is incomplete",
            priority="P2-medium",
            labels=["P2-medium", "enhancement", "backend"],
            body="Implement weather integration if issue #138 is not complete.\n\n**Depends on:** Verification of #138 status\n\n**Acceptance Criteria:**\n- Integrate with weather API\n- Fetch forecast data for routes\n- Display weather conditions in UI\n- Add weather-based recommendations"
        ),
        Issue(
            title="Implement actual TrainerRoad integration if #139 is incomplete",
            priority="P2-medium",
            labels=["P2-medium", "enhancement", "backend"],
            body="Implement TrainerRoad integration if issue #139 is not complete.\n\n**Depends on:** Verification of #139 status\n\n**Acceptance Criteria:**\n- Integrate with TrainerRoad API\n- Fetch workout calendar\n- Sync training plans\n- Display workouts in planner"
        ),
        Issue(
            title="Implement workout-aware logic if #140 is incomplete",
            priority="P2-medium",
            labels=["P2-medium", "enhancement", "backend"],
            body="Implement workout-aware recommendation logic if issue #140 is not complete.\n\n**Depends on:** Verification of #140 status\n\n**Acceptance Criteria:**\n- Consider scheduled workouts in recommendations\n- Avoid conflicts with training plans\n- Suggest recovery rides after hard workouts\n- Test with various workout schedules"
        ),
        Issue(
            title="Establish PR review requirements",
            priority="P2-medium",
            labels=["P2-medium", "documentation"],
            body="Define and document pull request review requirements.\n\n**Acceptance Criteria:**\n- Document required reviewers\n- Define review checklist\n- Set up branch protection rules\n- Create PR template"
        ),
        Issue(
            title="Long Rides: Implement skeleton loaders and error states",
            priority="P2-medium",
            labels=["P2-medium", "enhancement", "ux", "frontend"],
            body="Add skeleton loaders and proper error states to long rides feature.\n\n**Acceptance Criteria:**\n- Add skeleton loaders during data fetch\n- Implement error state UI\n- Add retry functionality\n- Test with slow/failed network conditions"
        ),
        Issue(
            title="Long Rides: Add accessibility features (WCAG 2.1 AA)",
            priority="P2-medium",
            labels=["P2-medium", "enhancement", "accessibility", "frontend"],
            body="Ensure long rides feature meets WCAG 2.1 AA accessibility standards.\n\n**Acceptance Criteria:**\n- Add ARIA labels and roles\n- Ensure keyboard navigation\n- Test with screen readers\n- Verify color contrast ratios\n- Add focus indicators"
        ),
    ]
    issues.extend(p2_issues)
    
    # P3-low issues (9 items)
    p3_issues = [
        Issue(
            title="Design: Verify mobile-first responsive design (320px viewport)",
            priority="P3-low",
            labels=["P3-low", "design", "frontend"],
            body="Verify all pages work correctly on 320px viewport (iPhone SE).\n\n**Acceptance Criteria:**\n- Test all pages at 320px width\n- Ensure no horizontal scrolling\n- Verify touch targets are accessible\n- Test on real iPhone SE device"
        ),
        Issue(
            title="Design: Ensure touch targets ≥44x44px with 8px spacing",
            priority="P3-low",
            labels=["P3-low", "design", "frontend", "accessibility"],
            body="Verify all interactive elements meet minimum touch target size.\n\n**Acceptance Criteria:**\n- Audit all buttons, links, inputs\n- Ensure 44x44px minimum size\n- Add 8px spacing between targets\n- Test on touch devices"
        ),
        Issue(
            title="Design: Verify WCAG AA contrast ratios (4.5:1)",
            priority="P3-low",
            labels=["P3-low", "design", "accessibility"],
            body="Verify all text meets WCAG AA contrast requirements.\n\n**Acceptance Criteria:**\n- Audit all text/background combinations\n- Ensure 4.5:1 ratio for normal text\n- Ensure 3:1 ratio for large text\n- Fix any failing combinations"
        ),
        Issue(
            title="Design: Test keyboard navigation and screen reader support",
            priority="P3-low",
            labels=["P3-low", "design", "accessibility"],
            body="Comprehensive keyboard and screen reader testing.\n\n**Acceptance Criteria:**\n- Test full keyboard navigation\n- Verify logical tab order\n- Test with NVDA/JAWS/VoiceOver\n- Document any issues found"
        ),
        Issue(
            title="Design: Test on real iOS/Android devices",
            priority="P3-low",
            labels=["P3-low", "design", "frontend", "testing"],
            body="Test application on real mobile devices (not just emulators).\n\n**Acceptance Criteria:**\n- Test on iPhone (iOS 15+)\n- Test on Android device (Android 11+)\n- Verify touch interactions\n- Test in various orientations\n- Document device-specific issues"
        ),
        Issue(
            title="Route naming improvements (Start → Main → End format)",
            priority="P3-low",
            labels=["P3-low", "enhancement", "backend"],
            body="Improve route naming to use Start → Main → End format.\n\n**Acceptance Criteria:**\n- Update naming algorithm\n- Sample 10 points along route\n- Generate descriptive names\n- Test with various route types"
        ),
        Issue(
            title="Reduce P1 issue count to <25",
            priority="P3-low",
            labels=["P3-low", "documentation"],
            body="Work to reduce the number of P1-high priority issues below 25.\n\n**Acceptance Criteria:**\n- Review all P1 issues\n- Close completed issues\n- Downgrade non-critical issues\n- Maintain P1 count below 25"
        ),
        Issue(
            title="Setup weekly maintenance routine",
            priority="P3-low",
            labels=["P3-low", "documentation"],
            body="Establish weekly maintenance routine for issue management.\n\n**Acceptance Criteria:**\n- Define maintenance checklist\n- Schedule weekly review time\n- Document process in README\n- Set up reminders"
        ),
        Issue(
            title="Implement GDPR-compliant data deletion endpoint",
            priority="P4-future",
            labels=["P4-future", "enhancement", "security"],
            body="Implement GDPR-compliant data deletion endpoint.\n\n**Note:** User is in US, not immediately needed, but good for future compliance.\n\n**Acceptance Criteria:**\n- Create DELETE endpoint for user data\n- Implement cascade deletion\n- Add confirmation workflow\n- Log deletion events\n- Test deletion completeness"
        ),
    ]
    issues.extend(p3_issues)
    
    return issues


def create_issue(issue: Issue, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Create a GitHub issue using the gh CLI.
    
    Args:
        issue: Issue object with title, labels, and body
        dry_run: If True, only print what would be created
        
    Returns:
        Tuple of (success, message)
    """
    labels_str = ",".join(issue.labels)
    
    if dry_run:
        print(f"\n[DRY RUN] Would create issue:")
        print(f"  Title: {issue.title}")
        print(f"  Labels: {labels_str}")
        if issue.body:
            print(f"  Body: {issue.body[:100]}...")
        return True, "Dry run - no issue created"
    
    try:
        cmd = [
            "gh", "issue", "create",
            "--title", issue.title,
            "--label", labels_str,
            "--body", issue.body if issue.body else issue.title
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        issue_url = result.stdout.strip()
        return True, f"Created: {issue_url}"
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else str(e)
        return False, f"Failed: {error_msg}"
    except FileNotFoundError:
        return False, "GitHub CLI (gh) not found. Please install it first."
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create GitHub issues from triaged todos"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview issues without creating them"
    )
    parser.add_argument(
        "--priority",
        choices=["P1-high", "P2-medium", "P3-low", "P4-future"],
        help="Only create issues with specified priority"
    )
    
    args = parser.parse_args()
    
    issues = get_issues()
    
    # Filter by priority if specified
    if args.priority:
        issues = [i for i in issues if i.priority == args.priority]
    
    if not issues:
        print("No issues to create.")
        return 0
    
    print(f"{'[DRY RUN] ' if args.dry_run else ''}Creating {len(issues)} issues...")
    print("=" * 80)
    
    success_count = 0
    failure_count = 0
    
    for i, issue in enumerate(issues, 1):
        print(f"\n[{i}/{len(issues)}] {issue.priority}: {issue.title}")
        
        success, message = create_issue(issue, dry_run=args.dry_run)
        
        if success:
            success_count += 1
            print(f"  ✓ {message}")
        else:
            failure_count += 1
            print(f"  ✗ {message}")
    
    print("\n" + "=" * 80)
    print(f"Summary: {success_count} succeeded, {failure_count} failed")
    
    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
