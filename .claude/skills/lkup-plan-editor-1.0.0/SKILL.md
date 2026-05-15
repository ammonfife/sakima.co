---
name: lkup-plan-editor
description: Edit lkup-plan.json (canonical architecture plan) and render lkup-plan.html
---

# lkup-plan Editor

Edit the canonical architecture plan and render the HTML version.

## Files

- **JSON**: `lkup-plan.json` (repo root) — THE source of truth
- **HTML**: `lkup-plan.html` (repo root) — human-readable, rendered from JSON
- **Render script**: `scripts/render-plan.cjs` (repo root) — regenerates HTML from JSON

## Edit Process

1. Read the section you're modifying first
2. Follow ownership rules (locked: mermaid arch/scan diagrams, Cloudflare POC)
3. Make your edit, keeping valid JSON
4. Bump `meta.version`, update `meta.last_updated`, add `version_history` entry
5. Validate: `python3 -c "import json; json.load(open('lkup-plan.json')); print('Valid')"`
6. Render HTML: `node scripts/render-plan.cjs`
7. Commit both files: `git add lkup-plan.json lkup-plan.html`

## Version History Entry
```json
{"version": "X.Y", "date": "YYYY-MM-DD", "author": "Codex", "summary": "Brief description"}
```
Add at position 0 in `version_history[]` (newest first).

## Bigmac Turso

After every plan edit, record as a fact and sync:
```bash
facts add operational "lkup-plan v[X.Y]: [summary]" --tags lkup,architecture,lkup-plan,agent:Codex,agent:bob
bigmac-sync push
```

### Tag Conventions
- **Project:** `lkup`, `consolidation`, `sakima`
- **Agents:** `agent:bob`, `agent:Codex`
- **Domain:** `architecture`, `lkup-plan`
- **Status:** `status:verified`, `status:inbox`
