# Create Triaged Issues Script

## Overview

The `create_triaged_issues.py` script automates the creation of GitHub issues from triaged todo items. It uses the GitHub CLI (`gh`) to create issues with appropriate labels and detailed descriptions.

## Prerequisites

1. **GitHub CLI installed**: Install from https://cli.github.com/
2. **Authenticated with GitHub**: Run `gh auth login` if not already authenticated
3. **Repository access**: Must have write access to create issues

## Usage

### Basic Usage

Create all issues:
```bash
python3 scripts/create_triaged_issues.py
```

### Dry Run Mode (Recommended First)

Preview what will be created without actually creating issues:
```bash
python3 scripts/create_triaged_issues.py --dry-run
```

### Filter by Priority

Create only specific priority issues:
```bash
# Create only P1-high issues
python3 scripts/create_triaged_issues.py --priority P1-high

# Create only P2-medium issues
python3 scripts/create_triaged_issues.py --priority P2-medium

# Dry run for P1 issues only
python3 scripts/create_triaged_issues.py --dry-run --priority P1-high
```

## Issue Breakdown

The script creates **34 total issues** across 4 priority levels:

- **P1-high**: 8 issues (critical UI/UX fixes and planner features)
- **P2-medium**: 17 issues (testing, logging, integrations)
- **P3-low**: 9 issues (design verification, process improvements)
- **P4-future**: 1 issue (GDPR compliance)

## Labels Applied

Issues are automatically labeled with:

### Priority Labels
- `P1-high` - Critical issues
- `P2-medium` - Important but not urgent
- `P3-low` - Nice to have
- `P4-future` - Long-term planning

### Category Labels
- `enhancement` - New features or improvements
- `bug` - Bug fixes
- `ui-ux` - User interface/experience
- `testing` - Test coverage improvements
- `security` - Security-related
- `documentation` - Documentation updates
- `code-quality` - Code quality improvements
- `accessibility` - Accessibility features
- `planner` - Planner feature
- `backend` - Backend changes
- `api` - API changes
- `process` - Process improvements

## Recommended Workflow

1. **First, run dry-run to preview**:
   ```bash
   python3 scripts/create_triaged_issues.py --dry-run
   ```

2. **Create P1 issues first**:
   ```bash
   python3 scripts/create_triaged_issues.py --priority P1-high
   ```

3. **Then create P2 issues**:
   ```bash
   python3 scripts/create_triaged_issues.py --priority P2-medium
   ```

4. **Create P3 and P4 as needed**:
   ```bash
   python3 scripts/create_triaged_issues.py --priority P3-low
   python3 scripts/create_triaged_issues.py --priority P4-future
   ```

## Error Handling

The script includes comprehensive error handling:

- **GitHub CLI not found**: Prompts to install `gh`
- **Authentication errors**: Prompts to run `gh auth login`
- **API rate limits**: Reports rate limit errors
- **Network errors**: Reports connection issues

## Output

The script provides detailed progress output:

```
Creating 34 issues...
================================================================================

[1/34] P1-high: Build planner frontend UI (currently placeholder only)
  ✓ Created: https://github.com/user/repo/issues/123

[2/34] P1-high: Add Marshmallow validation schemas for planner endpoints
  ✓ Created: https://github.com/user/repo/issues/124

...

================================================================================
Summary: 34 succeeded, 0 failed
```

## Troubleshooting

### "gh: command not found"
Install GitHub CLI: https://cli.github.com/

### "authentication required"
Run: `gh auth login`

### "permission denied"
Ensure you have write access to the repository

### Rate limit errors
Wait a few minutes and try again, or create issues in smaller batches using `--priority`

## Notes

- Each issue includes detailed acceptance criteria
- Issues reference related GitHub issues where applicable
- All issues follow the project's labeling conventions
- The script is idempotent - running it multiple times won't create duplicates (GitHub CLI handles this)