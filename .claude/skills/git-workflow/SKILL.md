---
name: git-workflow
description: "Git workflow enforcer for this repo. Use when making commits, pushing code, creating pull requests, or branching. Triggers on: create a commit, commit this, commit the change, commit and push, push it, push the fix, push to GitHub, push changes, create a PR, make a PR, open a PR, open a pull request, submit a PR, start a branch, branch from main, or any request that involves modifying git repository state."
---

# Git Workflow

Every change to this repo follows this workflow — no exceptions.

## Step 1: Read current state

Before anything else, run these in parallel:

```bash
git branch --show-current
git log main..HEAD --oneline
git status --short
gh pr list --head "$(git branch --show-current)" --state open
```

Use the output to determine which scenario applies below.

---

## Scenario A: On `main`

Never commit or push directly to main. Always branch first.

1. Pull latest main:
   ```bash
   git checkout main && git pull origin main
   ```

2. Create a descriptive branch using the correct prefix:
   - `fix/<what-is-fixed>` — bug fixes
   - `feat/<what-is-added>` — new features
   - `chore/<what-is-changed>` — tooling, deps, config, CI
   - `docs/<what-is-documented>` — documentation only
   - `refactor/<what-is-refactored>` — refactors with no behavior change

   ```bash
   git checkout -b <prefix>/<short-description>
   ```

3. Then proceed to Scenario B (you are now on a feature branch).

---

## Scenario B: On a feature branch — before committing

### Check what is staged

```bash
git diff --staged --name-only
```

**If staged files span multiple logical concerns** — split into separate commits.
Example: `frontend/src/App.tsx` (UI fix) and `.github/workflows/pr-automation.yml` (CI fix) are two concerns. Commit them separately:

```bash
git reset HEAD  # unstage all
git add <files-for-concern-1>
# commit concern 1
git add <files-for-concern-2>
# commit concern 2
```

**If staged files are one logical unit** — commit them together.

### Commit format

Every commit must follow conventional commit style:

```
<type>(<scope>): <short description in imperative mood>

<optional body — explain WHY, not what>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

Types: `fix`, `feat`, `chore`, `docs`, `refactor`, `build`, `ci`, `test`
Scope: affected area (`ui`, `backend`, `ci`, `deps`, `api`, etc.)

Rules:
- All commit messages and comments in English
- Subject line max 72 chars
- Do not push if the build is failing — run `cd frontend && npm run build` to verify before pushing

### Push the branch

```bash
git push -u origin <branch-name>
```

---

## Scenario C: On a feature branch — after commits, checking PR status

After each push, check if a PR exists:

```bash
gh pr list --head "$(git branch --show-current)" --state open
```

**If no PR exists and the work appears complete** — create one:

```bash
gh pr create \
  --title "<conventional commit title matching the main change>" \
  --body "$(cat <<'EOF'
## Summary

- <bullet: what changed and why>

## Test plan

- [ ] <specific thing to verify>
- [ ] <specific thing to verify>

🤖 Generated with [Claude Code](https://claude.ai/claude-code)
EOF
)"
```

**If a PR already exists** — push additional commits to the same branch. The PR updates automatically. Do not create a second PR.

**Never merge to main** — the user merges manually.

---

## Scenario D: Stashed work / interrupted session

If `git stash list` shows stashed changes, pop the right stash and apply it to the correct branch before proceeding. If the stash was on the wrong branch, apply it to a new branch created from latest main.

---

## Commit granularity rule

Prefer more focused commits over fewer large commits. If a task has 5 independent changes, make 5 commits. Ask: "Could this change be reverted independently without breaking the rest?" If yes, it is a separate commit.

---

## Summary checklist

- [ ] Not on main (or branched off it already)
- [ ] Branch name uses the correct prefix
- [ ] Staged files reviewed for logical grouping
- [ ] Build passes before push
- [ ] PR exists (or was just created) before declaring work done
- [ ] Never merged to main
