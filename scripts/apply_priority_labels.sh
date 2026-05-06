#!/bin/bash

# Apply Priority Labels Based on Intelligent Issue Management Recommendations
# Generated: 2026-05-06

set -e

echo "🏷️  Applying priority labels to unprioritized issues..."
echo ""

# High Priority (P1) - Core functionality and documentation
echo "📍 Labeling P1 (High Priority) issues..."
gh issue edit 119 --add-label "P1-high" && echo "  ✅ #119 - Update TECHNICAL_SPEC.md"
gh issue edit 118 --add-label "P1-high" && echo "  ✅ #118 - Re-enable geocoding after rate limit"
gh issue edit 117 --add-label "P1-high" && echo "  ✅ #117 - Fix map zoom to show start/finish"
gh issue edit 102 --add-label "P1-high" && echo "  ✅ #102 - Refactor report template JS"
echo ""

# Medium Priority (P2) - Quality of life improvements
echo "📍 Labeling P2 (Medium Priority) issues..."
gh issue edit 122 --add-label "P2-medium" && echo "  ✅ #122 - Grey out unselected routes"
gh issue edit 121 --add-label "P2-medium" && echo "  ✅ #121 - Color code route names"
gh issue edit 116 --add-label "P2-medium" && echo "  ✅ #116 - Visual weather icons"
gh issue edit 115 --add-label "P2-medium" && echo "  ✅ #115 - Optimal departure time suggestions"
gh issue edit 114 --add-label "P2-medium" && echo "  ✅ #114 - Transit recommendations"
gh issue edit 113 --add-label "P2-medium" && echo "  ✅ #113 - Wind-based route recommendations"
gh issue edit 112 --add-label "P2-medium" && echo "  ✅ #112 - Weather severity indicators"
gh issue edit 111 --add-label "P2-medium" && echo "  ✅ #111 - Evening commute window"
gh issue edit 110 --add-label "P2-medium" && echo "  ✅ #110 - Morning commute window"
gh issue edit 109 --add-label "P2-medium" && echo "  ✅ #109 - 7-day forecast card layout"
gh issue edit 108 --add-label "P2-medium" && echo "  ✅ #108 - Integrate forecast generator"
gh issue edit 107 --add-label "P2-medium" && echo "  ✅ #107 - Interactive map for long rides"
gh issue edit 106 --add-label "P2-medium" && echo "  ✅ #106 - Average speed and elevation metrics"
gh issue edit 105 --add-label "P2-medium" && echo "  ✅ #105 - Monthly ride statistics"
echo ""

# Low Priority (P3) - Nice-to-have features
echo "📍 Labeling P3 (Low Priority) issues..."
gh issue edit 120 --add-label "P3-low" && echo "  ✅ #120 - Bootstrap tab switching"
gh issue edit 49 --add-label "P3-low" && echo "  ✅ #49 - Metric/Imperial unit toggle"
gh issue edit 48 --add-label "P3-low" && echo "  ✅ #48 - Data export (JSON/GPX/CSV)"
gh issue edit 46 --add-label "P3-low" && echo "  ✅ #46 - PDF export option"
gh issue edit 45 --add-label "P3-low" && echo "  ✅ #45 - QR code generation"
gh issue edit 44 --add-label "P3-low" && echo "  ✅ #44 - Extract HTML template"
echo ""

# Future Enhancements (P4) - Long-term features
echo "📍 Labeling P4 (Future Enhancements) issues..."
gh issue edit 68 --add-label "P4-future" && echo "  ✅ #68 - Visual Hierarchy & Polish"
gh issue edit 67 --add-label "P4-future" && echo "  ✅ #67 - Mobile Navigation Patterns"
gh issue edit 66 --add-label "P4-future" && echo "  ✅ #66 - Feature Discovery & Onboarding"
gh issue edit 65 --add-label "P4-future" && echo "  ✅ #65 - Touch-Optimized Interactions"
gh issue edit 64 --add-label "P4-future" && echo "  ✅ #64 - Progressive Disclosure for Metrics"
gh issue edit 63 --add-label "P4-future" && echo "  ✅ #63 - Mobile-First Responsive Layout"
gh issue edit 62 --add-label "P4-future" && echo "  ✅ #62 - EPIC: Mobile-First UI/UX Redesign"
gh issue edit 39 --add-label "P4-future" && echo "  ✅ #39 - Evaluate Photon API"
gh issue edit 38 --add-label "P4-future" && echo "  ✅ #38 - Social features"
gh issue edit 37 --add-label "P4-future" && echo "  ✅ #37 - Real-time route suggestions"
gh issue edit 36 --add-label "P4-future" && echo "  ✅ #36 - Mobile app version"
gh issue edit 35 --add-label "P4-future" && echo "  ✅ #35 - Integration with other platforms"
echo ""

echo "✅ Priority labeling complete!"
echo ""
echo "📊 Summary:"
echo "  - P1 (High): 4 issues labeled"
echo "  - P2 (Medium): 14 issues labeled"
echo "  - P3 (Low): 6 issues labeled"
echo "  - P4 (Future): 12 issues labeled"
echo "  - Total: 36 issues labeled"
echo ""
echo "Next steps:"
echo "  1. Run: ./scripts/update-issue-priorities.sh > ISSUE_PRIORITIES.md"
echo "  2. Review the updated ISSUE_PRIORITIES.md"
echo "  3. Commit changes: git add ISSUE_PRIORITIES.md && git commit -m 'docs: Apply priority labels from intelligent issue management'"

# Made with Bob
