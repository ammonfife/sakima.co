---
name: work-on
description: "Universal project orientation skill. Accepts any repo name as argument: /work-on lkup.info, /work-on heimdall-archive, /work-on lemons, etc. Self-identifies platform, finds the repo, reads the knowledge snapshot and AGENTS.md, checks open todos, and prints a ready-state summary. Works on local machine, Devin VM, Codex, cloud sandboxes. The single correct starting point for any agent picking up any project."
user-invocable: true
---

# /work-on <repo-name>

Universal orientation skill. Invoke as `/work-on lkup.info`, `/work-on heimdall-archive`, etc.
No arg = defaults to the most recently active project from WORKFLOW_AUTO.md.

---

## Step 0 — Self-identify platform and find repo

```bash
REPO_NAME="${1:-}"  # e.g. "lkup.info", "heimdall-archive", "lemons"

# Detect platform by checking which paths exist
if [ -d "$HOME/github/ammonfife/$REPO_NAME" ]; then
    REPO="$HOME/github/ammonfife/$REPO_NAME"
    PLATFORM="local"
elif [ -d "$HOME/repos/$REPO_NAME" ]; then
    REPO="$HOME/repos/$REPO_NAME"
    PLATFORM="devin-vm"
elif [ -d "/workspace/$REPO_NAME" ]; then
    REPO="/workspace/$REPO_NAME"
    PLATFORM="cloud-sandbox"
else
    echo "❌ Repo '$REPO_NAME' not found in any known path"
    echo "   Checked: ~/github/ammonfife/, ~/repos/, /workspace/"
    echo "   Available: $(ls ~/github/ammonfife/ 2>/dev/null | tr '\n' ' ')"
    exit 1
fi

echo "Platform: $PLATFORM | Repo: $REPO"
cd "$REPO"
```

**If no repo name given:** read WORKFLOW_AUTO.md to find the active thread, then infer the repo.
```bash
grep "THREAD:.*START" ~/.claude/projects/-Users-benfife/WORKFLOW_AUTO.md 2>/dev/null | head -5
# Pick the most recently updated thread's project → use that repo
```

---

## Step 1 — Git state

```bash
cd "$REPO"
BRANCH=$(git branch --show-current 2>/dev/null)
AHEAD=$(git rev-list @{u}..HEAD 2>/dev/null | wc -l | tr -d ' ')
DIRTY=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')

echo "Branch: $BRANCH | Ahead: $AHEAD commits | Dirty: $DIRTY files"

# Pull latest
git checkout prod 2>/dev/null || git checkout main 2>/dev/null || true
git pull 2>/dev/null | tail -2
```

**If not on `prod`:** warn loudly — all work in ammonfife repos goes on `prod`, never `main`.

---

## Step 2 — Read project knowledge (in priority order)

```bash
# 1. Knowledge snapshot (Turso facts/todos/policies — most important)
[ -f lkup_knowledge.md ] && echo "=== lkup_knowledge.md ===" && head -100 lkup_knowledge.md
[ -f heimdall_knowledge.md ] && echo "=== heimdall_knowledge.md ===" && head -60 heimdall_knowledge.md
# Generic: find any *_knowledge.md at repo root
for f in *_knowledge.md *-knowledge.md; do [ -f "$f" ] && head -80 "$f"; done

# 2. Current punch list
[ -f NEXT_SESSION.md ] && echo "=== NEXT_SESSION.md ===" && cat NEXT_SESSION.md

# 3. Execution policy
[ -f AGENTS.md ] && echo "=== AGENTS.md (first 60 lines) ===" && head -60 AGENTS.md

# 4. Architecture (if large project)
[ -f CLAUDE.md ] && echo "=== CLAUDE.md (first 40 lines) ===" && head -40 CLAUDE.md
```

---

## Step 3 — Check open todos (Turso)

```bash
# Local (BigMac CLI):
todo list --tags="$REPO_NAME" --status=open --limit=15 2>/dev/null || \
  todo list --tags=lkup --status=open --limit=15 2>/dev/null

# Cloud (HTTP — works from Devin VM, Codex, any sandbox):
TURSO_URL="libsql://bigmac-ammonfife.aws-us-west-2.turso.io"
source .env 2>/dev/null  # TURSO_AUTH_TOKEN should be in .env
if [ -n "$TURSO_AUTH_TOKEN" ]; then
    curl -s -X POST "https://bigmac-ammonfife.aws-us-west-2.turso.io/v2/pipeline" \
      -H "Authorization: Bearer $TURSO_AUTH_TOKEN" -H "Content-Type: application/json" \
      -d "{\"requests\":[{\"type\":\"execute\",\"stmt\":{\"sql\":\"SELECT id,task,status FROM todos WHERE tags LIKE '%${REPO_NAME}%' AND status='pending' ORDER BY id DESC LIMIT 15\"}},{\"type\":\"close\"}]}" \
      2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
rows=d.get('results',[{}])[0].get('response',{}).get('result',{}).get('rows',[])
for r in rows: print(f'  #{r[0][\"value\"]} {r[1][\"value\"][:80]}')
" 2>/dev/null
fi
```

---

## Step 4 — Platform-specific connection strings

**Local machine:**
```bash
# Supabase service role key
LKUP_KEY=$(python3 -c "import json; d=json.load(open('/Users/benfife/.claude/settings.json')); print(d.get('env',{}).get('LKUP_SUPABASE_SERVICE_ROLE_KEY',''))" 2>/dev/null)

# Turso token
TURSO_TOKEN=$(security find-generic-password -a bigmac -s turso-bigmac-token -w 2>/dev/null)
```

**Devin VM / Cloud sandbox:**
```bash
source .env  # All keys should be in .env at repo root
# LKUP_SUPABASE_SERVICE_ROLE_KEY, TURSO_AUTH_TOKEN, etc.
# See agent/context/devin.md or agent/context/poke.md for HTTP endpoints
```

**Per-platform context files:**
```bash
cat agent/context/claude.md 2>/dev/null    # Claude Code local
cat agent/context/devin.md 2>/dev/null     # Devin VM
cat agent/context/poke.md 2>/dev/null      # Poke / cloud
cat agent/context/mog.md 2>/dev/null       # mog@gptagency.ai
```

---

## Step 5 — Ready-state summary

Output exactly this before starting work:

```
✅ /work-on <repo-name>
─────────────────────────────────────────────────────────────
  Platform:     <local|devin-vm|cloud-sandbox>
  Repo:         <full path>
  Branch:       <branch> | <N> commits ahead | <N> dirty files
  Knowledge:    <snapshot name> (<age>h old, hook=<wired|MISSING>)
  Open todos:   <N> pending
  Connection:   Supabase <OK|MISSING> | Turso <OK|MISSING>
─────────────────────────────────────────────────────────────
  RULES: prod branch only | fix on discovery | real data only
         push after every block | ~/clawd = ~/bigmac-state
```

Then proceed with whatever task was requested.

---

## Project-specific overrides

When invoked for a known project, load these in priority order:

| Repo | What's authoritative |
|---|---|
| `lkup.info` | **Read in this order:** (1) `NEXT_SESSION.md` — operating rules + punch list + what was shipped last session. (2) `docs/integrity/CURRENT_PLAN.md` Section 7 — commit drift audit, migration tracker gap. (3) `docs/integrity/WIRING.md` — full WIRED/UNWIRED/BROKEN map. (4) `bash scripts/verify-wiring.sh` — actual pipeline state. Then run `/work-on-lkup` for full architecture context. **NOT** `lkup-plan.json` alone — it is outdated and has not been maintained since recovery work 2026-05-09. **Do NOT run `supabase db push`** — migration tracker divergence, see CURRENT_PLAN.md Section 7. |
| `heimdall-archive` | `/work-on-heimdall` skill (15-year methodology context, IP stance) |
| Any other | This skill alone is sufficient |

**lkup.info deploy note:** Lovable has its own build + deploy pipeline. **NOT Vercel.** Git push → Lovable auto-fetches → Lovable builds → Lovable deploys to lkup.info. The `/lovable-deploy` skill handles clicking the Publish button.

```bash
# Auto-load project skill ONLY for heimdall (others use lkup_knowledge.md instead)
if [ "$REPO_NAME" = "heimdall-archive" ]; then
    [ -f "$HOME/.claude/skills/work-on-heimdall/SKILL.md" ] && \
        echo "Also loading: /work-on-heimdall" && \
        head -80 "$HOME/.claude/skills/work-on-heimdall/SKILL.md"
fi
```

---

## One-liner invocations

```bash
# Start on lkup.info
/work-on lkup.info

# Start on heimdall
/work-on heimdall-archive

# Start fresh — pick up where WORKFLOW_AUTO.md left off
/work-on
```
