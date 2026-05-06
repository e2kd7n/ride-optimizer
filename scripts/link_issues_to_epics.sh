#!/bin/bash

# Link Issues to Epic Parents
# Web Platform Epic: #144
# Weather Dashboard Epic: #145

set -e

echo "🔗 Linking issues to their epic parents..."
echo ""

# Link Web Platform issues to Epic #144
echo "📋 Linking Web Platform issues to Epic #144..."

# Phase 1: Foundation Squad
gh issue edit 129 --body "$(gh issue view 129 --json body -q .body)

**Part of Epic:** #144 (Web Platform Migration)
**Squad:** Foundation Squad
**Phase:** 1 - Backend Infrastructure" && echo "  ✅ #129 linked"

gh issue edit 130 --body "$(gh issue view 130 --json body -q .body)

**Part of Epic:** #144 (Web Platform Migration)
**Squad:** Foundation Squad
**Phase:** 1 - Backend Infrastructure" && echo "  ✅ #130 linked"

gh issue edit 131 --body "$(gh issue view 131 --json body -q .body)

**Part of Epic:** #144 (Web Platform Migration)
**Squad:** Foundation Squad
**Phase:** 1 - Backend Infrastructure" && echo "  ✅ #131 linked"

gh issue edit 137 --body "$(gh issue view 137 --json body -q .body)

**Part of Epic:** #144 (Web Platform Migration)
**Squad:** Foundation Squad
**Phase:** 1 - Backend Infrastructure" && echo "  ✅ #137 linked"

# Phase 2: Frontend Squad
gh issue edit 132 --body "$(gh issue view 132 --json body -q .body)

**Part of Epic:** #144 (Web Platform Migration)
**Squad:** Frontend Squad
**Phase:** 2 - Core Views
**Dependencies:** #129, #130, #131" && echo "  ✅ #132 linked"

gh issue edit 133 --body "$(gh issue view 133 --json body -q .body)

**Part of Epic:** #144 (Web Platform Migration)
**Squad:** Frontend Squad
**Phase:** 2 - Core Views
**Dependencies:** #129, #130, #131" && echo "  ✅ #133 linked"

gh issue edit 134 --body "$(gh issue view 134 --json body -q .body)

**Part of Epic:** #144 (Web Platform Migration)
**Squad:** Frontend Squad
**Phase:** 2 - Core Views
**Dependencies:** #129, #130, #131" && echo "  ✅ #134 linked"

gh issue edit 135 --body "$(gh issue view 135 --json body -q .body)

**Part of Epic:** #144 (Web Platform Migration)
**Squad:** Frontend Squad
**Phase:** 2 - Core Views
**Dependencies:** #129, #130, #131" && echo "  ✅ #135 linked"

# Phase 3: Integration Squad
gh issue edit 136 --body "$(gh issue view 136 --json body -q .body)

**Part of Epic:** #144 (Web Platform Migration)
**Squad:** Integration Squad
**Phase:** 3 - Feature Integration
**Dependencies:** #129, #130, #131" && echo "  ✅ #136 linked"

gh issue edit 138 --body "$(gh issue view 138 --json body -q .body)

**Part of Epic:** #144 (Web Platform Migration)
**Squad:** Integration Squad
**Phase:** 3 - Feature Integration
**Dependencies:** #129, #130, #131" && echo "  ✅ #138 linked"

gh issue edit 139 --body "$(gh issue view 139 --json body -q .body)

**Part of Epic:** #144 (Web Platform Migration)
**Squad:** Integration Squad
**Phase:** 3 - Feature Integration
**Dependencies:** #129, #130, #131" && echo "  ✅ #139 linked"

gh issue edit 140 --body "$(gh issue view 140 --json body -q .body)

**Part of Epic:** #144 (Web Platform Migration)
**Squad:** Integration Squad
**Phase:** 3 - Feature Integration
**Dependencies:** #129, #130, #131" && echo "  ✅ #140 linked"

# Phase 4: QA Squad
gh issue edit 99 --body "$(gh issue view 99 --json body -q .body)

**Part of Epic:** #144 (Web Platform Migration)
**Squad:** QA Squad
**Phase:** 4 - Polish & Quality" && echo "  ✅ #99 linked"

gh issue edit 100 --body "$(gh issue view 100 --json body -q .body)

**Part of Epic:** #144 (Web Platform Migration)
**Squad:** QA Squad
**Phase:** 4 - Polish & Quality" && echo "  ✅ #100 linked"

gh issue edit 101 --body "$(gh issue view 101 --json body -q .body)

**Part of Epic:** #144 (Web Platform Migration)
**Squad:** QA Squad
**Phase:** 4 - Polish & Quality" && echo "  ✅ #101 linked"

gh issue edit 142 --body "$(gh issue view 142 --json body -q .body)

**Part of Epic:** #144 (Web Platform Migration)
**Squad:** QA Squad
**Phase:** 4 - Polish & Quality" && echo "  ✅ #142 linked"

gh issue edit 143 --body "$(gh issue view 143 --json body -q .body)

**Part of Epic:** #144 (Web Platform Migration)
**Squad:** QA Squad
**Phase:** 4 - Polish & Quality" && echo "  ✅ #143 linked"

echo ""

# Link Weather Dashboard issues to Epic #145
echo "📋 Linking Weather Dashboard issues to Epic #145..."

gh issue edit 54 --body "$(gh issue view 54 --json body -q .body)

**Part of Epic:** #145 (Weather Dashboard)
**Phase:** Parent Epic" && echo "  ✅ #54 linked"

gh issue edit 108 --body "$(gh issue view 108 --json body -q .body)

**Part of Epic:** #145 (Weather Dashboard)
**Phase:** 3 - Integration" && echo "  ✅ #108 linked"

gh issue edit 109 --body "$(gh issue view 109 --json body -q .body)

**Part of Epic:** #145 (Weather Dashboard)
**Phase:** 1 - Forecast Display" && echo "  ✅ #109 linked"

gh issue edit 110 --body "$(gh issue view 110 --json body -q .body)

**Part of Epic:** #145 (Weather Dashboard)
**Phase:** 1 - Forecast Display" && echo "  ✅ #110 linked"

gh issue edit 111 --body "$(gh issue view 111 --json body -q .body)

**Part of Epic:** #145 (Weather Dashboard)
**Phase:** 1 - Forecast Display" && echo "  ✅ #111 linked"

gh issue edit 112 --body "$(gh issue view 112 --json body -q .body)

**Part of Epic:** #145 (Weather Dashboard)
**Phase:** 1 - Forecast Display" && echo "  ✅ #112 linked"

gh issue edit 113 --body "$(gh issue view 113 --json body -q .body)

**Part of Epic:** #145 (Weather Dashboard)
**Phase:** 2 - Intelligent Recommendations" && echo "  ✅ #113 linked"

gh issue edit 114 --body "$(gh issue view 114 --json body -q .body)

**Part of Epic:** #145 (Weather Dashboard)
**Phase:** 2 - Intelligent Recommendations" && echo "  ✅ #114 linked"

gh issue edit 115 --body "$(gh issue view 115 --json body -q .body)

**Part of Epic:** #145 (Weather Dashboard)
**Phase:** 2 - Intelligent Recommendations" && echo "  ✅ #115 linked"

gh issue edit 116 --body "$(gh issue view 116 --json body -q .body)

**Part of Epic:** #145 (Weather Dashboard)
**Phase:** 1 - Forecast Display" && echo "  ✅ #116 linked"

echo ""
echo "✅ All issues linked to their epic parents!"
echo ""
echo "📊 Summary:"
echo "  - Web Platform Epic (#144): 17 issues linked"
echo "  - Weather Dashboard Epic (#145): 10 issues linked"
echo "  - Total: 27 issues organized"

# Made with Bob
