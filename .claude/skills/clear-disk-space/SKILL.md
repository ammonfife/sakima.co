# /clear-disk-space — Safe Disk Space Analysis & Recovery

**Trigger:** User explicitly types `/clear-disk-space` or asks to free up disk space.

**HARD RULE: This skill is AUDIT-ONLY until the user explicitly approves each action.**
Never execute any deletion, move, or compression autonomously.
Present findings → wait for explicit "run it" / "go ahead" / "do it" → then act.
"Finding disk space" ≠ authorization. Silence ≠ authorization.

---

## Approval protocol

Before executing ANY disk action:
1. Show exactly what will be affected (path, size, type)
2. Explain what it is and whether it's recoverable
3. Wait for explicit approval using one of: "run it", "go ahead", "do it", "yes", "trash it"
4. If user says anything ambiguous — ask once for clarification, then wait

---

## NEVER touch these (no exceptions, no matter what)

| Category | Paths | Why |
|---|---|---|
| Photos cache | `~/Library/Caches/com.apple.Photos*`, Photos Library | Face recognition, thumbnails — DAYS to rebuild |
| Spotlight index | `.Spotlight-V100`, `com.apple.Spotlight` | Full disk index — 1-3 DAYS to rebuild on large drives |
| Email caches | `icloudmailagent`, `com.apple.icloudmailagent` | Mail sync state — DAYS to re-sync |
| ML/CoreData caches | Any `CoreData`, `com.apple.ml.*` | Model caches — hours/days to rebuild |
| User documents | `~/Documents`, `~/Desktop`, `~/Downloads` | Ben uses Downloads as Documents — treat as irreplaceable |
| Active repo copies | Any `* copy N` folder | May contain unique uncommitted work — read DIFF.md first |
| `.git` directories | Any `.git` | HARD BAN — never delete |

---

## Safe analysis tools (run these, never ask permission)

```bash
# Overall disk picture
dust -d 2 ~ 2>/dev/null | head -40

# Repo copy status
cat ~/github/ammonfife/COPIES.md 2>/dev/null

# Cross-repo lineage (what's unique in ancestor repos)
cat ~/github/ammonfife/lkup.info/LINEAGE.md 2>/dev/null

# Structural folder dupes
cat ~/github/ammonfife/SUBFOLDER_DUPES.md 2>/dev/null

# Homebrew cache (safe to clean)
du -sh ~/Library/Caches/Homebrew 2>/dev/null

# Package manager download caches
du -sh ~/.npm/_cacache ~/Library/Caches/pip 2>/dev/null

# node_modules in copy repos (NOT canonical repos)
find ~/github/ammonfife -name "node_modules" -type d -prune 2>/dev/null \
  | grep -E "copy|backup" \
  | xargs -I{} python3 -c "import subprocess,sys; r=subprocess.run(['du','-sh','{}'],capture_output=True,text=True); print(r.stdout.strip())" 2>/dev/null \
  | sort -rh | head -20

# What's in Trash right now
du -sh ~/.Trash/ 2>/dev/null
```

---

## Approved action categories (only with explicit "run it")

### 🟢 Zero-risk (propose, then run on approval)
- `brew cleanup --prune=all` — Homebrew download cache only
- `pip cache purge` — pip wheel cache only
- Empty Trash — only when user explicitly says "empty trash"

### 🟡 Low-risk (show specific paths first, wait for approval per-item)
- `dist/` and `build/` artifacts in INACTIVE copy repos only
- `node_modules` in confirmed-inactive copy repos (after DIFF.md reviewed)
- Old session JSONL files (>90 days, after confirming no unique context)

### 🔴 Never autonomous (requires explicit per-item confirmation + DIFF.md review)
- Anything in copy repos (`* copy N`, `*-backup-*`)
- Anything in `~/Documents`, `~/Desktop`, `~/Downloads`
- Any `.mbox` or email data
- Any database files (`.db`, `.sqlite`)

---

## Pre-Trash-Empty Safety Audit

Run this BEFORE emptying Trash. Verifies every non-auto-generated file in Trash has a canonical (non-backup) copy outside Trash:

```bash
python3 ~/bin/trash-safety-audit.py
```

Script at `~/bin/trash-safety-audit.py` — checks three things:
1. **Truly orphaned** — file in Trash, no copy anywhere → RESTORE before emptying
2. **Backup-only** — file in Trash, "canonical" copy is itself in a backup folder → RESTORE
3. **Confirmed canonical** — live copy exists in a non-copy, non-backup location → safe

---

## Parallel-Tree Merge Check

Before removing ANY backup/copy folder, verify it has no unique files the canonical lacks:

```bash
python3 ~/bin/parallel-tree-check.py ~/github/ammonfife
# Reports: files in copy dirs with no canonical equivalent
# These must be merged INTO canonical before backup is safe to remove
```

**Known parallel trees needing merge (as of 2026-05-12):**
- `github/_local_backups/` — 8,552 unique files including auth credentials
- `Documents/GitHubGitHub_corrupted/` — 6,583 unique old BigMac workspace files
- `github/Morebackupstuff/` — 5,320 unique pre-commit auth backups
- `Documents/codebackup/` — 4,429 timestamped old agent scripts
- `github/ammonfife/BIGMAC copy*/` — each has unique source files per copy
- Use `backup-diff ~/github/ammonfife` to regenerate per-copy DIFF.md

**Merge protocol — NO REGRESSION RULE (with file-type nuance):**

Three cases when a file exists in backup AND canonical at the same relative path:

**Case A: Identical hash** → backup is a true dupe. Discard backup copy. ✅

**Case B: Same path, different hash — CODE FILE (.py, .ts, .js, .sh, .rb, .go, etc.)**
- Do NOT overwrite canonical. Do NOT discard backup.
- Run `diff -u canonical/path backup/path` line by line.
- Present the diff. Only cherry-pick specific lines/blocks if they represent genuinely unique logic.
- Use a git branch in the canonical repo. Never merge directly to prod/main.
- The canonical repo's git history is the source of truth.

**Case C: Same path, different hash — NON-CODE FILE (docs, data, xlsx, pdf, etc.)**
- Do NOT overwrite canonical. Do NOT discard backup.
- Keep BOTH: canonical stays as-is, backup is renamed with a date suffix.
- Example: `report.xlsx` stays, backup becomes `report_backup_20241013.xlsx` alongside it.
- User reviews both at their own pace.

**Path only in backup (no canonical equivalent):**
- Code: copy to a git branch, review before merging
- Non-code: copy directly, no branch needed
- Safe command: `rsync -av --ignore-existing backup_tree/ canonical_tree/`

**Rule:** A backup tree is only safe to remove when its parallel-tree-check shows 0 unique files.

---

## Tools reference

| Tool | Install | Use |
|---|---|---|
| `dust` | `brew install dust` | Fast visual disk usage |
| `subfolder-dupes` | `~/bin/subfolder-dupes` | Find structurally duplicated folder trees |
| `backup-diff` | `~/bin/backup-diff` | Generate DIFF.md + COPIES.md for all repo copies |
| `repo-lineage` | `~/bin/repo-lineage` | Generate LINEAGE.md cross-repo archaeology |
| `jdupes -S` | already installed | Audit-only: find byte-identical files (never use --link-hard on backups) |
| `shasum -a 256` | built-in | Verify two specific files are identical before acting |

---

## Screenshots during this skill

Ben has 3 large monitors. ALWAYS use targeted screenshots:
```bash
peekaboo screenshot --app "Finder" --output ~/clawd/data/disk-screenshot.png
# Never: screencapture -x /tmp/full.png
```

---

## Full System Tidy Plan

See `~/clawd/data/system-tidy-plan-2026-05-12.md` for the complete 7-phase plan covering:
- Phase 0: Safety baseline (verify Backblaze, run pre-trash audit)
- Phase 1: Parallel tree merges (auth credentials, GitHubGitHub_corrupted, codebackup)
- Phase 2: Repo copy consolidation (BIGMAC + lkup.info copies via DIFF.md=0 gate)
- Phase 3: Documents reorganization (remaining dupes from 434k-line jdupes report)
- Phase 4: node_modules policy (retire with copies, not standalone)
- Phase 5: iCloud Drive organization (132GB, already iCloud-backed)
- Phase 6: Photos duplicates (Photos.app built-in Duplicates album)
- Phase 7: Ongoing maintenance schedule

**Space estimate:** 75-100GB additional recoverable across all phases.
**Current state:** 121GB free on 5.5TB. Target: ~200GB free.

---

## Key facts about this machine

- **Drive:** 5.5TB, ~120GB free
- **Biggest folders:** `~/github/ammonfife/` (~640GB), `~/Documents` (~210GB), `~/Movies` (148GB), `~/Desktop` (~140GB)
- **Downloads is NOT ephemeral** — Ben uses it as Documents. Treat as irreplaceable.
- **Production machine** — repos are live code. Breaking a running repo = breaking production.
- **Backblaze** installed at `/Library/Backblaze.bzpkg/` — check coverage before any action
- **iCloud sync:** `~/Documents` and `~/Desktop` ARE iCloud-synced (`com.apple.icloud.desktop` xattr confirmed). 30-day recovery window.
- **GitHub sync:** `~/github/ammonfife/*` and `~/bigmac-state` are git repos pushed to GitHub — committed content is safe. Uncommitted/unstaged content and copy repos (not separately pushed) are Backblaze-only.
- **Backblaze only:** `~/Movies`, `~/Pictures`, `~/Downloads` — no git, no cloud recovery.
- **iCloud placeholders** — some files in iCloud-synced dirs may be cloud-only (not downloaded locally). Check `st_blocks == 0` before comparing hashes.
