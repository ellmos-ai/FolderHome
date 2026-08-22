# Workflow: Release new npm package version

**English** | [Deutsch](./_example-workflow.de.md)

> **Last verified:** 2026-08-21  
> **Frequency:** per Release (ad-hoc)  
> **Duration:** ~5 min

## Purpose

Publish a new version of an npm package, including version bump, build, test, Git tag, push and verify. With Dependabot upstream sync if needed.

## Preconditions

- `npm whoami` shows you as an authenticated user
- You are on the correct branch (usually `main` or `master`)
- `git status` is clean except for the planned changes
- You are an admin of the repo (for branch protection bypass if needed)

## Steps

1. **Version bump** in `package.json`  
   ```bash
   # Manuell oder via:
   npm version patch   # oder minor/major
   ```


2. **Sync package-lock.json**  
   ```bash
   npm install --package-lock-only
   ```


3. **Build**  
   ```bash
   npm run build
   ```


4. **Tests** (if present)  
   ```bash
   npm test
   ```


5. **Commit**  
   ```bash
   git add package.json package-lock.json dist/
   git commit -m "chore: bump version to $(node -p "require('./package.json').version")"
   ```


6. **Rebase if behind**  
   ```bash
   git fetch origin
   git status -b --porcelain=v1 | head -1
   # Wenn "behind": git pull --rebase
   ```


7. **Push**  
   ```bash
   git push
   ```


8. **Publish**  
   ```bash
   npm publish --access public
   ```


9. **Verify**  
   ```bash
   npm view $(node -p "require('./package.json').name") version
   ```


## Exit-Criteria

- [ ] `git status` is clean
- [ ] `npm view ... version` shows the new version
- [ ] No open branch-protection error
- [ ] `CHANGELOG.md` entry updated (if release-worthy)
- [ ] `STATE.md` updated

## Pitfalls

- ⚠️ **Branch 2 commits behind**: This often happens when a bot has pushed in the meantime (e.g., Dependabot, CI workflow sync). Always `git pull --rebase` before your own push.  
- ⚠️ **`prepublishOnly` fails**: Often due to unset NODE_OPTIONS causing TypeScript OOM. Fix: `NODE_OPTIONS="--max-old-space-size=8192" npm publish`  
- ⚠️ **Force-push required due to a faulty commit**: Use a vetted project-specific admin playbook, not `git push --force` directly.

## Related

- `workflows/security-audit.md` — if the project creates its own security playbook for this  
- [`../SECURITY.md`](../SECURITY.md) — Safety boundaries for npm/git operations

## History

- **2026-08-21** — Workflow created from [Project context]  
- **2026-08-21** — Step 6 (rebase-check) added after friction incident
