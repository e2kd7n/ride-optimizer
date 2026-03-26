#!/bin/bash
set -e
echo "Creating UI/UX Epic..."
EPIC_NUMBER=$(gh issue create --title "🎨 EPIC: Mobile-First UI/UX Redesign" --label "epic,ui-ux,mobile-responsive,P2-medium,enhancement" --body "See UIUX_IMPROVEMENTS_EPIC.md for details" --json number --jq '.number')
echo "Epic created: #$EPIC_NUMBER"

gh issue create --title "📱 Mobile-First Responsive Layout" --label "ui-ux,mobile-responsive,P1-high,enhancement" --body "Part of Epic #$EPIC_NUMBER - See UIUX_IMPROVEMENTS_EPIC.md"
gh issue create --title "📊 Progressive Disclosure for Metrics" --label "ui-ux,enhancement,P2-medium" --body "Part of Epic #$EPIC_NUMBER - See UIUX_IMPROVEMENTS_EPIC.md"
gh issue create --title "👆 Touch-Optimized Interactions" --label "ui-ux,mobile-responsive,P1-high,enhancement" --body "Part of Epic #$EPIC_NUMBER - See UIUX_IMPROVEMENTS_EPIC.md"
gh issue create --title "🎓 Feature Discovery & Onboarding" --label "ui-ux,enhancement,P2-medium" --body "Part of Epic #$EPIC_NUMBER - See UIUX_IMPROVEMENTS_EPIC.md"
gh issue create --title "📱 Mobile Navigation Patterns" --label "ui-ux,mobile-responsive,P2-medium,enhancement" --body "Part of Epic #$EPIC_NUMBER - See UIUX_IMPROVEMENTS_EPIC.md"
gh issue create --title "✨ Visual Hierarchy & Polish" --label "ui-ux,enhancement,P3-low" --body "Part of Epic #$EPIC_NUMBER - See UIUX_IMPROVEMENTS_EPIC.md"
gh issue create --title "🗺️ Map Direction Indicators" --label "ui-ux,enhancement,P2-medium" --body "Part of Epic #$EPIC_NUMBER - See DESIGN_PRINCIPLES.md Section 6"

echo "All issues created!"
