#!/bin/bash
set -e
echo "Creating UI/UX Epic..."
EPIC_NUMBER=$(gh issue create --title "🎨 EPIC: Mobile-First UI/UX Redesign" --label "enhancement,ux,design,P2-medium,frontend" --body "See UIUX_IMPROVEMENTS_EPIC.md for details" --json number --jq '.number')
echo "Epic created: #$EPIC_NUMBER"

gh issue create --title "📱 Mobile-First Responsive Layout" --label "ux,design,P1-high,enhancement,frontend" --body "Part of Epic #$EPIC_NUMBER - See UIUX_IMPROVEMENTS_EPIC.md"
gh issue create --title "📊 Progressive Disclosure for Metrics" --label "ux,enhancement,P2-medium,frontend" --body "Part of Epic #$EPIC_NUMBER - See UIUX_IMPROVEMENTS_EPIC.md"
gh issue create --title "👆 Touch-Optimized Interactions" --label "ux,P1-high,enhancement,frontend" --body "Part of Epic #$EPIC_NUMBER - See UIUX_IMPROVEMENTS_EPIC.md"
gh issue create --title "🎓 Feature Discovery & Onboarding" --label "ux,enhancement,P2-medium,frontend" --body "Part of Epic #$EPIC_NUMBER - See UIUX_IMPROVEMENTS_EPIC.md"
gh issue create --title "📱 Mobile Navigation Patterns" --label "ux,design,P2-medium,enhancement,frontend" --body "Part of Epic #$EPIC_NUMBER - See UIUX_IMPROVEMENTS_EPIC.md"
gh issue create --title "✨ Visual Hierarchy & Polish" --label "ux,design,enhancement,P3-low,frontend" --body "Part of Epic #$EPIC_NUMBER - See UIUX_IMPROVEMENTS_EPIC.md"
gh issue create --title "🗺️ Map Direction Indicators" --label "ux,enhancement,P2-medium,frontend" --body "Part of Epic #$EPIC_NUMBER - See DESIGN_PRINCIPLES.md Section 6"

echo "All issues created!"
