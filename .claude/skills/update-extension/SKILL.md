---
name: update-extension
description: Bump lkup.info Chrome extension version and remind to reload
trigger: /update-extension
---

@~/.claude/skills/lkup-shared-context/CONTEXT.md

# /update-extension

Run after ANY change to files in `~/github/ammonfife/lkup.info/extension/`.

## Steps (mandatory, every time):

1. **Bump version** in `extension/manifest.json`:
   - Read current version
   - Increment patch (1.15.0 → 1.16.0)
   - Write new version

2. **Log changes** — append to `extension/CHANGELOG.md` (create if missing):
   ```
   ## v1.X.0 — YYYY-MM-DD
   - [change 1]
   - [change 2]
   ```

3. **Remind user to reload**:
   ```
   Extension bumped to v1.X.0. Reload in Chrome:
   chrome://extensions → lkup.info → reload button
   ```

## HARD RULES:
- **ALWAYS bump version** — never ship extension changes without a version bump
- Bump patch for fixes, minor for features, major for breaking changes
- The version in manifest.json is what Chrome displays — it must match the actual code state
- Never skip this skill when editing extension files

## Files that trigger this skill:
- `extension/content/*.js`
- `extension/background/*.js`
- `extension/lib/*.js`
- `extension/manifest.json`
- `extension/popup/*`
