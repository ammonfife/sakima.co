# mac-dedupe-cleanup — Safe Disk Space Recovery for Hoarders

**Trigger:** User asks about disk space, cleanup, duplicates, freeing space on Mac, deduplication, storage full, "file (1) (54)" duplicates, organizing Downloads/Documents, or "agents nuked my files."

**Philosophy:** PRESERVE ALL UNIQUE USER/AGENT-CREATED WORK. Disk space is the secondary concern.  
Organize → Compress → Archive. Deletion requires explicit per-file authorization — never autonomous.  
"Finding disk space" means building a map, not taking action. Present candidates; wait for "run it."  
This machine IS the production environment. Every copy was created intentionally. Treat it that way.

**NEVER delete these caches — they take DAYS to rebuild:**
- **Photos cache** (`~/Library/Caches/com.apple.Photos*`, `~/Pictures/Photos Library.photoslibrary/`) — face recognition, thumbnail generation, ML models
- **Spotlight index** (`~/.Spotlight-V100/`, `~/Library/Caches/com.apple.Spotlight`) — full disk index, takes 1-3 days on large drives
- **Email/iCloud mail caches** (`icloudmailagent`, `com.apple.icloudmailagent`, `com.apple.iCloudNotificationAgent`) — mail sync state, attachment index, takes days to re-sync
- Any ML/vision/CoreData model cache

**What is NOT a useful space strategy:**
- `__pycache__` / `.pyc` — regenerate within seconds of next Python run. Net savings: 0. Cost: slower cold starts.
- Any actively-used cache — clearing makes current work slower and caches refill immediately.
- Do NOT use `jdupes --link-hard` on backup copies — hardlinks share the same inode; modifying live file silently changes the "backup" too.

**What IS removable (with explicit authorization only):**
- `dist/` and `build/` artifacts in INACTIVE copy repos only (recompilable from source in live repo)
- Package manager DOWNLOAD caches (separate from installed packages): `brew cleanup`, `pip cache purge`
- `node_modules` only in confirmed-inactive copies after user says "run it"

---

## Context: Ben's Disk Profile (as of 2026-05-11)

| Folder | Size | Risk Level |
|--------|------|------------|
| `~/github` | 701 GB | 🟢 Safe wins (node_modules, .git pack) |
| `~/Documents` | 230 GB | 🔴 Treat as irreplaceable |
| `~/Movies` | 148 GB | 🟡 Review manually |
| `~/Desktop` | 139 GB | 🔴 Treat as irreplaceable (used as Documents) |
| `~/bigmac-state` | 63 GB | 🟡 Logs + session archives |
| `~/Pictures` | 63 GB | 🔴 Never touch without explicit permission |
| `~/Downloads` | 7.1 GB | 🔴 Treat as Documents — NOT ephemeral |
| `~/.claude` + Claude app | 17 GB | 🟡 Session JSONL + skills (mostly safe) |

**Free space:** ~68 GB on 5.5 TB drive (tight — ~1.2% free).

---

## Hard Rules for This Machine

1. **NEVER mass-delete `~/Downloads`** — previous agent nuked it and caused real data loss.
2. **NEVER treat `file (1).ext` through `file (54).ext` as automatic duplicates** — system preserved them because contents may differ (different tool runs, different data). Hash-compare FIRST.
3. **NEVER delete from `~/Documents`, `~/Desktop`, `~/Downloads`, `~/Pictures` without showing Ben what will be removed and getting confirmation in that turn.**
4. **Repos must stay working** — no deleting `.git`, no removing files that are actively referenced by running code.
5. **Use `trash` not `rm -rf`** — always recoverable from Trash until emptied.
6. **jdupes with `--link-hard` is preferred over deletion** — APFS hardlinks recover space without removing the file from any path.

---

## Phase 0: Quick Wins (Zero Risk, Do Now)

These are safe to run without asking:

```bash
# Homebrew cache (redownloadable, typically 2-10 GB)
brew cleanup --prune=all 2>/dev/null
du -sh ~/Library/Caches/Homebrew 2>/dev/null

# npm/yarn/pnpm cache (redownloadable)
npm cache clean --force 2>/dev/null
du -sh ~/.npm/_cacache 2>/dev/null

# pip cache
pip cache purge 2>/dev/null

# macOS system caches (OS rebuilds automatically)
sudo rm -rf ~/Library/Caches/com.apple.dt.Xcode 2>/dev/null

# Empty Trash (only if Ben confirms)
# osascript -e 'tell application "Finder" to empty trash'
```

---

## Phase 1: The Big Win — ~/github (701 GB)

This is where the real space is. Safe targets:

### 1a. Find and remove node_modules in INACTIVE repos

```bash
# AUDIT FIRST — see what's there
find ~/github -name "node_modules" -type d -prune 2>/dev/null \
  | while read d; do du -sh "$d" 2>/dev/null; done \
  | sort -rh | head -30

# Check which repos have recent git activity (last 90 days)
find ~/github -name "node_modules" -type d -prune 2>/dev/null \
  | while read d; do
      repo=$(echo "$d" | sed 's|/node_modules||')
      last=$(git -C "$repo" log -1 --format="%ar" 2>/dev/null || echo "not-a-repo")
      echo "$last | $d"
    done | sort
```

**Only remove node_modules from repos with no git activity in 90+ days AND that aren't currently running:**
```bash
# Safe delete — reinstallable with npm install
trash ~/github/<inactive-repo>/node_modules
```

### 1b. Deduplicate .git pack files across repos (jdupes hardlink)

Multiple repos often share identical git pack objects (forks, clones of same upstream):

```bash
# AUDIT: find duplicates across all .git/objects directories — report only, no changes
jdupes -r -S ~/github --exclude="!*.git/objects/*" 2>/dev/null | head -50

# SAFE DEDUP with hardlinks (space recovered, file accessible from all paths)
# jdupes -r -L ~/github/  ← DO NOT RUN without reviewing audit output first
```

### 1c. Build artifacts

```bash
# Rust target/ directories (recompilable)
find ~/github -name "target" -type d -prune 2>/dev/null \
  | xargs du -sh 2>/dev/null | sort -rh | head -20

# Python __pycache__ and .pyc (safe to remove, Python recreates)
find ~/github -name "__pycache__" -type d -prune -exec du -sh {} \; 2>/dev/null | sort -rh | head -20
# find ~/github -name "__pycache__" -type d -prune -exec trash {} \; 2>/dev/null
```

---

## Phase 2: Deduplication Workflow (Hash-Based, Ben's Way)

### The right way to find real duplicates

```bash
# Install jdupes if needed (already installed on this machine)
# brew install jdupes

# STEP 1: AUDIT ONLY — find duplicates by content hash, show what would change
# -r = recursive, -S = show sizes, NO -d or -L flag = read-only report
jdupes -r -S ~/Documents 2>/dev/null > /tmp/dupes-documents.txt
wc -l /tmp/dupes-documents.txt
head -50 /tmp/dupes-documents.txt
```

### Understanding jdupes output

Each duplicate GROUP looks like:
```
--- Duplicate group 1 (42.3 MB each, 3 files) ---
/Users/benfife/Documents/report.pdf
/Users/benfife/Documents/backup/report.pdf
/Users/benfife/Downloads/report (1).pdf   ← may or may not be same data
```

**CRITICAL:** `file (1).pdf` appearing in a group means it IS byte-identical to another file. If it's NOT in a group, it's unique content — keep it.

### Handling the `file (1) (54)` question

```bash
# To check if two specific files are identical:
shasum -a 256 "file.pdf" "file (1).pdf"
# Same hash = identical content. Different hash = different data — BOTH are unique.

# To get a full hash inventory of a directory:
find ~/Downloads -type f -exec shasum -a 256 {} \; 2>/dev/null > ~/clawd/data/downloads-hashes-$(date +%Y%m%d).txt
```

### ⚠️ DO NOT use jdupes --link-hard on backup copies

Hardlinks make two paths point to the SAME inode. If either path is modified, BOTH change.
This silently destroys the backup copy's value as a snapshot.
Only safe for truly static, never-independently-modified content (binary assets, etc.).
For backup copies of repos: leave as separate inodes. The space cost IS the protection.

**Instead: APFS clones** (`cp -c`) give copy-on-write divergence — safe for backups,
but only useful when creating NEW copies, not deduplicating existing ones.

### The nuclear option (move to trash, not delete)

```bash
# If hardlinks aren't enough and Ben wants actual deletion:
# -d = delete mode (interactive), -r = recursive
# jdupes -r -d ~/Documents/backups/  ← interactive, asks for each group
```

---

## Phase 3: ~/Desktop + ~/Documents Strategy

These are irreplaceable. The right moves are **organize** and **archive**, not delete.

### Audit what's there

```bash
# Top 20 largest files in Documents
find ~/Documents -type f -exec du -sh {} \; 2>/dev/null | sort -rh | head -20

# Top 20 largest files on Desktop
find ~/Desktop -type f -exec du -sh {} \; 2>/dev/null | sort -rh | head -20

# Find files older than 2 years (candidates for cold archive)
find ~/Documents -type f -mtime +730 2>/dev/null | head -30

# Find video files (often large and forgotten)
find ~/Documents ~/Desktop ~/Downloads -type f \( -name "*.mp4" -o -name "*.mov" -o -name "*.mkv" -o -name "*.avi" \) \
  -exec du -sh {} \; 2>/dev/null | sort -rh | head -20
```

### Safe archive strategy

Rather than deleting, compress + move to cold storage:

```bash
# Create a dated archive of old Desktop items
ARCHIVE_DATE=$(date +%Y-%m-%d)
mkdir -p ~/clawd/data/desktop-archive-$ARCHIVE_DATE
# mv specific items there — never bulk move

# For large old folders: zip and keep the zip
# zip -r ~/Documents/archive-$ARCHIVE_DATE.zip ~/Documents/old-project-folder/
# Then trash the original AFTER verifying the zip
```

---

## Phase 4: ~/bigmac-state (63 GB)

Session archives and logs — mostly safe to compress:

```bash
# Find large log files
find ~/bigmac-state -name "*.log" -size +10M 2>/dev/null | xargs du -sh | sort -rh | head -20

# Find old scope recordings (stream-*.json files — gitignored, often large)
find ~/bigmac-state/scope -name "stream-*.json" 2>/dev/null | xargs du -sh 2>/dev/null | sort -rh | head -10

# Session archives older than 30 days
find ~/bigmac-state -name "*.jsonl" -mtime +30 2>/dev/null | xargs du -sh | sort -rh | head -20
```

---

## Phase 5: Claude Session Files (~/.claude + App Support)

```bash
# Old JSONL session files (conversation transcripts)
du -sh ~/.claude/projects/*/*.jsonl 2>/dev/null | sort -rh | head -20

# Claude Desktop cache/logs
du -sh ~/Library/Application\ Support/Claude/ 2>/dev/null

# Safe to remove: very old completed session transcripts
# find ~/.claude/projects -name "*.jsonl" -mtime +90 -exec du -sh {} \; | sort -rh | head -10
```

---

## Tools Reference

| Tool | Install | Best For |
|------|---------|----------|
| `jdupes` | ✅ already installed | Hash dedup, hardlink dedup |
| `mole` (`mo`) | `brew install tw93/tap/mole` | Interactive disk explorer |
| `dust` | `brew install dust` | Fast visual `du` replacement |
| `ncdu` | `brew install ncdu` | TUI disk usage navigator |
| `shasum -a 256` | built-in | Verify two files are identical |
| `trash` | `brew install trash` | Safe delete (recoverable) |
| `diskdedupe` | Mac App Store | APFS-native GUI dedup |

---

## Quick Start (Run This First)

```bash
# 1. Get a full picture in 60 seconds
brew install dust 2>/dev/null || true
dust -d 2 ~ 2>/dev/null | head -40

# 2. See your biggest git repos
du -sh ~/github/*/ 2>/dev/null | sort -rh | head -20

# 3. Find node_modules eating space
find ~/github -name "node_modules" -type d -prune 2>/dev/null \
  -exec du -sh {} \; | sort -rh | head -20

# 4. Homebrew cleanup (safe, always)
brew cleanup --prune=all

# 5. Check jdupes version
jdupes --version
```

---

## What NOT To Do (Learned the Hard Way)

- ❌ `rm -rf ~/Downloads` — was used as Documents, caused data loss
- ❌ Bulk-treating `file (1).ext` as dupes without hash check — they may be different data
- ❌ `docker system prune` — may kill active containers
- ❌ `git gc --aggressive` on active repos — can corrupt in-progress operations
- ❌ Removing `.git` directories — **HARD RULE**, blocks running code
- ❌ Deleting `node_modules` in active repos without checking if they're running
- ❌ Any bulk operation without a dry-run audit first
