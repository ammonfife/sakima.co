#!/opt/homebrew/bin/bash
# switch-accounts: toggle Claude Code login between sakima.lc@gmail.com and ammonfife@gmail.com
#
# Keychain model (discovered 2026-04-18):
#   - Claude Code CLI stores OAuth per-email as:
#       service=claude_code_oauth_token, account=<email>
#   - There is also a "default" entry (acct=<uid>) used when no acct is specified
#   - `anthropic-oauth-<name>` and `anthropic-refresh-<name>` are legacy/backup banks
#     (may be stale — never trust as source of truth)
#
# The skill:
#   - reads per-email entries as canonical
#   - freshens legacy banks from per-email values (append-only update)
#   - sets the "default" entry to the target email's token
#   - exports CLAUDE_CODE_OAUTH_TOKEN, updates ~/.zshrc to always read from keychain
#   - quits + relaunches Desktop (optional)
#   - backs up /tmp/ artifacts + snapshots state before swapping
#   - never deletes keychain entries, never overwrites memory files

set -eo pipefail

LOG_ROOT="$HOME/clawd/backups"
ME="$(id -un)"

# -------- known accounts --------
SAKIMA_EMAIL="sakima.lc@gmail.com"
AMMON_EMAIL="ammonfife@gmail.com"
SAKIMA_ORG="490d42cb-5811-4685-bad6-03d9e74d651f"
AMMON_ORG="d2d4e3ca-34da-48ab-bf95-9f3327f688d7"

usage() {
  cat <<EOF
Usage: $(basename "$0") [target] [flags]

Target (positional OR flag form — any of these work):
  sakima    | --sakima           force switch to sakima.lc@gmail.com
  ammonfife | --ammonfife        force switch to ammonfife@gmail.com
  toggle    | --toggle            (default) flip to whichever login isn't current

Behavior flags:
  --dry-run                  print the plan, don't execute
  --skip-backup              skip /tmp rescue (fast path)
  --bounce-desktop           ALSO quit + relaunch Claude Desktop
                             (NOT default — Desktop is left alone unless this is set)
  --i-ran-exit-protocol      required alongside --bounce-desktop; asserts that
                             /exit-protocol was already run in every active session
  --allow-concurrent         proceed even when other \`claude\` CLI sessions are alive
                             (default aborts and tells you to /exit-protocol those first)
  --trust-token              skip the \`claude auth status\` probe entirely; trust
                             whatever is in keychain. Use when the CLI is
                             rate-limited or unresponsive and you just want the
                             keychain flipped so the NEXT claude invocation
                             picks up the right account.
  --skip-exit-protocol-check skip the pre-flight gate that checks for a recent
                             /exit-protocol marker in memory/today.md.
                             Only use in emergencies (rate-limit escape, etc.).
  -h, --help                 show this help

Safety model (Ben's rules, 2026-04-18):
  - switch-accounts automatically requires /exit-protocol to have been run FIRST.
    The script greps memory/today.md for a checkpoint or end-of-session marker
    in the last 2 minutes. If missing, abort. Override with
    --skip-exit-protocol-check.
  - /exit-protocol does NOT switch accounts. The two skills are unidirectional.
  - switch.sh NEVER auto-quits Claude Desktop. To bounce, pass --bounce-desktop AND
    --i-ran-exit-protocol (the double-flag forces you to save state first).
  - If other \`claude\` CLI sessions are running, switch.sh aborts unless
    --allow-concurrent is set. Run /exit-protocol in those first.
  - Claude (the assistant) MUST invoke /exit-protocol BEFORE running this script.
EOF
}

FORCE=""
DRY=0
SKIP_BACKUP=0
BOUNCE_DESKTOP=0
EXIT_PROTOCOL_RAN=0
ALLOW_CONCURRENT=0
TRUST_TOKEN=0
SKIP_EXIT_PROTOCOL_CHECK=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    sakima|ammonfife|toggle)    FORCE="$1"; shift ;;
    --sakima)                   FORCE="sakima"; shift ;;
    --ammonfife)                FORCE="ammonfife"; shift ;;
    --toggle)                   FORCE="toggle"; shift ;;
    --dry-run)                  DRY=1; shift ;;
    --skip-backup)              SKIP_BACKUP=1; shift ;;
    --bounce-desktop)           BOUNCE_DESKTOP=1; shift ;;
    --i-ran-exit-protocol)      EXIT_PROTOCOL_RAN=1; shift ;;
    --allow-concurrent)         ALLOW_CONCURRENT=1; shift ;;
    --trust-token)              TRUST_TOKEN=1; shift ;;
    --skip-exit-protocol-check) SKIP_EXIT_PROTOCOL_CHECK=1; shift ;;
    # legacy: --no-desktop was the old "skip" flag when bouncing was the default.
    # Now that non-bouncing IS the default, --no-desktop is a no-op kept for backwards compat.
    --no-desktop)               shift ;;
    -h|--help)                  usage; exit 0 ;;
    *)                          echo "unknown arg: $1"; usage; exit 2 ;;
  esac
done
export TRUST_TOKEN

# ---------- pre-flight gate: /exit-protocol must have run recently IN THIS SESSION ----------
# Directional rule (Ben 2026-04-18): switch-accounts requires /exit-protocol to have
# run FIRST. The reverse is NOT true — /exit-protocol does not switch accounts.
#
# Gate requires BOTH:
#   (a) a marker line containing `claude@<MY_SESSION_SHORT>` — i.e. written by
#       THIS session, not a sibling. Another session's /exit-protocol doesn't
#       save THIS session's in-progress work.
#   (b) HH:MM from that marker within 2 minutes of now.
#
# Accepted marker formats (anchored to line-start `## `):
#   ## [HH:MM MDT claude@<short-id>] 🗜️ PRE-COMPACT CHECKPOINT ...
#   ## [HH:MM MDT claude@<short-id>] END OF SESSION ...
#
# Exit-protocol skill MUST use `~/bin/my-claude-session-id | cut -d- -f1` to
# derive the short id so labels match what this gate searches for.
# Dry-run skips the gate (it's a pure preview).
TODAY_MD="$HOME/.claude/projects/-Users-benfife/memory/today.md"
if [[ $DRY -eq 0 && $SKIP_EXIT_PROTOCOL_CHECK -eq 0 ]]; then
  MY_SID_FULL=$(~/bin/my-claude-session-id 2>/dev/null || true)
  MY_SID_SHORT="${MY_SID_FULL%%-*}"
  if [[ -z "$MY_SID_SHORT" ]]; then
    cat >&2 <<EOM
/switch-accounts: could not determine my own session id (walk-up failed).
This blocks the exit-protocol gate because there's no way to verify THIS
session ran /exit-protocol. Pass --skip-exit-protocol-check to override.
EOM
    exit 5
  fi
  HAS_MARKER=0
  if [[ -f "$TODAY_MD" ]]; then
    # Find marker lines for MY session id, grab the most recent
    MARKER_LINE=$(grep -E "claude@${MY_SID_SHORT}[^]]*\].*(PRE-COMPACT CHECKPOINT|END OF SESSION)" "$TODAY_MD" | tail -1)
    if [[ -n "$MARKER_LINE" ]]; then
      MARKER_HHMM=$(echo "$MARKER_LINE" | sed -nE 's/.*\[([0-9]{1,2}):([0-9]{2})[^]]*\].*/\1:\2/p')
      if [[ -n "$MARKER_HHMM" ]]; then
        MARKER_MIN=$(echo "$MARKER_HHMM" | awk -F: '{print $1*60+$2}')
        NOW_MIN=$(( $(date +%H) * 60 + $(date +%M) ))
        DELTA=$(( NOW_MIN - MARKER_MIN ))
        # 5-min negative grace for clock drift, 2-min positive window (DELTA >= -5 && DELTA <= 2)
        if [[ $DELTA -ge -5 && $DELTA -le 2 ]]; then
          HAS_MARKER=1
        fi
      fi
    fi
  fi
  if [[ $HAS_MARKER -eq 0 ]]; then
    # Show diagnostic: did we find any marker for this session at all?
    LAST_OWN_MARKER=$(grep -E "claude@${MY_SID_SHORT}[^]]*\].*(PRE-COMPACT CHECKPOINT|END OF SESSION)" "$TODAY_MD" 2>/dev/null | tail -1 | head -c 120)
    cat >&2 <<EOM
/switch-accounts: no /exit-protocol marker from THIS session within last 2 min.

switch-accounts requires /exit-protocol to run FIRST (per Ben's rule 2026-04-18),
AND the marker must be from THIS session — another session's exit-protocol
doesn't save THIS session's in-progress work.

My session id:  ${MY_SID_SHORT} (full: ${MY_SID_FULL})
Latest marker from me: ${LAST_OWN_MARKER:-<none>}
Gate requires marker timestamp within 2 min of now ($(date +%H:%M)).

What to do:
  1. Run /exit-protocol (default "compact" mode is fine — basic saves everything).
     The skill MUST use \`~/bin/my-claude-session-id | cut -d- -f1\` for labeling
     so this gate can match it.
  2. Re-run this command within 2 minutes.

Escape hatch (emergencies only, e.g. rate-limit escape):
  --skip-exit-protocol-check
EOM
    exit 5
  fi
fi

# ---------- peer-session check (multi-agent / same-agent multi-session) ----------
# Count other `claude` CLI processes owned by this user, excluding ourselves.
# We look for node-running-claude: the CLI is a node script, so we match on the claude entrypoint.
MY_PID=$$
MY_PPID=$PPID
# Direct-match the CLI: the node process whose argv[1] ends in /cli.js under a claude dir, or a 'claude' wrapper.
PEERS=$(ps -axo pid,user,command 2>/dev/null \
  | awk -v me="$ME" '$2==me && $0 ~ /(\/claude\/cli\.js|\/claude$| claude(\s|$)| claude --)/ {print $1}' \
  | grep -v -E "^($MY_PID|$MY_PPID)$" || true)
PEER_COUNT=$(echo "$PEERS" | grep -cE '^[0-9]+$' || echo 0)

if [[ $PEER_COUNT -gt 0 && $ALLOW_CONCURRENT -eq 0 ]]; then
  cat >&2 <<EOM
/switch-accounts: $PEER_COUNT other claude CLI session(s) running as $ME.
PIDs: $(echo "$PEERS" | tr '\n' ' ')

Those sessions hold the OLD token in memory. Switching now would leave them running
on the outgoing login until they restart, which can clobber work-in-progress.

What to do:
  1. In each of those sessions, run /exit-protocol to save state.
  2. Exit (/exit or Ctrl+D) each session.
  3. Re-run this command.

Or, if you've already saved state and just want to proceed (e.g. you know those
sessions are idle), pass --allow-concurrent.
EOM
  exit 3
fi

if [[ $BOUNCE_DESKTOP -eq 1 && $EXIT_PROTOCOL_RAN -eq 0 ]]; then
  cat >&2 <<EOM
/switch-accounts: --bounce-desktop requires --i-ran-exit-protocol.

Quitting Claude Desktop without first running /exit-protocol in every active
Desktop session risks losing in-progress chats, drafts, and Cowork state.

What to do:
  1. In every active Claude Desktop window, run /exit-protocol (or the equivalent
     save-state flow).
  2. Re-run with: --bounce-desktop --i-ran-exit-protocol
EOM
  exit 4
fi

email_of() {
  case "$1" in sakima) echo "$SAKIMA_EMAIL" ;; ammonfife) echo "$AMMON_EMAIL" ;; esac
}
org_of() {
  case "$1" in sakima) echo "$SAKIMA_ORG" ;; ammonfife) echo "$AMMON_ORG" ;; esac
}

kc_read_by_acct() { security find-generic-password -s "$1" -a "$2" -w 2>/dev/null || true; }
kc_read()         { security find-generic-password -s "$1" -w 2>/dev/null || true; }
kc_write_acct()   { security add-generic-password -s "$1" -a "$2" -w "$3" -U 2>/dev/null; }

# -------- detect current --------
# Canonical source: which per-email entry currently matches the "default" entry
DEFAULT_TOK="$(kc_read claude_code_oauth_token)"
SAK_TOK="$(kc_read_by_acct claude_code_oauth_token "$SAKIMA_EMAIL")"
AMM_TOK="$(kc_read_by_acct claude_code_oauth_token "$AMMON_EMAIL")"

CURRENT="unknown"
if [[ -n "$DEFAULT_TOK" && -n "$SAK_TOK" && "$DEFAULT_TOK" == "$SAK_TOK" ]]; then
  CURRENT="sakima"
elif [[ -n "$DEFAULT_TOK" && -n "$AMM_TOK" && "$DEFAULT_TOK" == "$AMM_TOK" ]]; then
  CURRENT="ammonfife"
fi

# -------- pick target --------
if [[ "$FORCE" == "sakima" || "$FORCE" == "ammonfife" ]]; then
  TARGET="$FORCE"
else
  case "$CURRENT" in
    sakima)    TARGET="ammonfife" ;;
    ammonfife) TARGET="sakima" ;;
    *)         TARGET="sakima" ;;
  esac
fi

if [[ "$CURRENT" == "$TARGET" ]]; then
  MODE="resync"  # same-login: re-apply all derived state (keychain default, org-id, zshrc, Desktop) without an identity swap
else
  MODE="switch"
fi

# ---------- broadcast to peer sessions: save state NOW ----------
# Ben's rule (2026-04-18): switch-accounts must inbox all active sessions
# telling them to run /exit-protocol before the switch finalizes. This gives
# peers a chance to save their in-progress work before their OAuth token
# effectively becomes stale. Self-consumption guard on the reader side skips
# this session's own copy. Dry-run skips (don't spam inbox on previews).
if [[ $DRY -eq 0 ]]; then
  MY_SID=$(~/bin/my-claude-session-id 2>/dev/null || true)
  INBOX="$HOME/.claude/projects/-Users-benfife/.inbox"
  if [[ -n "$MY_SID" ]]; then
    {
      echo "[Session $MY_SID → ALL OTHER SESSIONS] 🔄 SWITCH-ACCOUNTS BROADCAST"
      echo "  Account switch starting: $CURRENT → $TARGET (mode=$MODE)"
      echo "  Your OAuth token will NOT change mid-process (you hold it in memory),"
      echo "  but shared keychain/zshenv/launchctl state is being rewritten."
      echo "  Run /exit-protocol NOW to durably save your work. Safe to continue"
      echo "  this session after that — restart only if you want to pick up the"
      echo "  new account's token yourself."
      echo "  Broadcast at $(date '+%Y-%m-%d %H:%M:%S %Z')"
      echo ""
    } >> "$INBOX"
    echo "  📬 broadcast sent to $INBOX (peers will see on next tool use)"
  else
    echo "  ⚠️  could not determine my session id — skipping peer broadcast"
  fi
fi

printf "\n== /switch-accounts ==\n"
printf "  mode    : %s\n" "$MODE"
printf "  current : %s (%s)\n" "$CURRENT" "$(email_of "$CURRENT" 2>/dev/null || echo unknown)"
printf "  target  : %s (%s)\n" "$TARGET" "$(email_of "$TARGET")"
if [[ "$MODE" == "resync" ]]; then
  printf "  note    : target == current — forcing full resync (keychain, zshrc, Desktop bounce)\n"
fi
[[ $DRY -eq 1 ]] && { echo "  dry-run : yes — no changes"; exit 0; }

# -------- 1. backup --------
BK="$LOG_ROOT/switch-accounts-$(date +%Y%m%d-%H%M%S)-${CURRENT}-to-${TARGET}"
mkdir -p "$BK"
echo
echo "[1/7] backup → $BK"

if [[ $SKIP_BACKUP -eq 0 ]]; then
  mkdir -p "$BK/tmp-rescue"
  find /tmp -maxdepth 4 -user "$ME" -type f -mtime -1 \
      \( -name '*.log' -o -name '*.json' -o -name '*.md' -o -name '*.txt' \
         -o -name '*.sh' -o -name '*.py' -o -name '*.js' -o -name '*.ts' \
         -o -name '*.html' -o -name '*.csv' \) \
      ! -name '*.lock' ! -name '*.pid' ! -name '*.sock' \
      -print0 2>/dev/null | xargs -0 -I {} cp -p {} "$BK/tmp-rescue/" 2>/dev/null || true
  N=$(find "$BK/tmp-rescue" -type f 2>/dev/null | wc -l | tr -d ' ')
  echo "    rescued $N /tmp file(s)"
fi

{
  echo "=== pre-switch keychain snapshot $(date) ==="
  for S in claude_code_oauth_token anthropic-oauth-sakima anthropic-oauth-ammonfife anthropic-refresh-sakima anthropic-refresh-ammonfife claude-ai-org-id; do
    for A in "$ME" "$SAKIMA_EMAIL" "$AMMON_EMAIL" ""; do
      if [[ -z "$A" ]]; then V=$(kc_read "$S"); else V=$(kc_read_by_acct "$S" "$A"); fi
      if [[ -n "$V" ]]; then printf "%-42s acct=%-25s len=%3d head=%s\n" "$S" "${A:-<default>}" "${#V}" "${V:0:14}..."; fi
    done
  done
} > "$BK/keychain-snapshot.txt"
cp ~/.zshrc "$BK/zshrc.pre" 2>/dev/null || true

# -------- 2. append-only sync --------
echo "[2/7] append-sync shared state"
nohup claude-sync push >"$BK/claude-sync.log" 2>&1 &
TODAY_MD="$HOME/.claude/projects/-Users-benfife/memory/today.md"
if [[ -f "$TODAY_MD" ]]; then
  {
    echo
    if [[ "$MODE" == "resync" ]]; then
      echo "## [$(date +%H:%M) MDT switch-accounts] resync $TARGET"
    else
      echo "## [$(date +%H:%M) MDT switch-accounts] $CURRENT → $TARGET"
    fi
    echo "- mode: $MODE"
    echo "- backup: \`$BK\`"
    echo "- active: $(email_of "$TARGET")"
  } >> "$TODAY_MD"
fi

# -------- 3. resolve target token --------
# This step must survive an already-rate-limited API because the whole point of
# the skill is sometimes to ESCAPE a rate limit by flipping accounts.
# Strategy:
#   - Read target token from keychain (offline, always works).
#   - Validate with `claude auth status`, but: (a) timeout 5s so it can't hang,
#     (b) on ANY non-"explicit stale" signal (including rate-limit, network
#     error, timeout, 5xx), TRUST THE TOKEN — rate-limit ≠ invalid token.
#   - --trust-token flag skips validation entirely; used when the CLI itself is
#     unresponsive and you just need the keychain flipped.
echo "[3/7] resolve target token for $TARGET"
TARGET_EMAIL="$(email_of "$TARGET")"
TARGET_TOK="$(kc_read_by_acct claude_code_oauth_token "$TARGET_EMAIL")"
NEED_FRESH=0
if [[ -z "$TARGET_TOK" ]]; then
  echo "    no live token for $TARGET_EMAIL — will run claude setup-token"
  NEED_FRESH=1
elif [[ ${TRUST_TOKEN:-0} -eq 1 ]]; then
  echo "    --trust-token set: skipping claude auth status probe"
else
  # Bounded check: 5s timeout, capture stdout+stderr, don't fail the script on non-zero.
  CHECK="$(timeout 5 env CLAUDE_CODE_OAUTH_TOKEN="$TARGET_TOK" claude auth status 2>&1 || true)"
  # ONLY treat as stale if the CLI returns an explicit auth-failure signal.
  # Everything else (rate limit, network error, timeout, 5xx, unrecognized output)
  # is treated as "token is probably fine, proceed".
  if echo "$CHECK" | grep -qiE '"loggedIn"[[:space:]]*:[[:space:]]*false|not authenticated|token expired|invalid token|revoked|unauthorized|401'; then
    echo "    token explicitly stale: $(echo "$CHECK" | head -1 | head -c 120)"
    NEED_FRESH=1
  elif echo "$CHECK" | grep -qiE 'rate limit|rate.limited|quota|429|too many requests'; then
    echo "    validation blocked by rate-limit — token assumed valid, proceeding"
  elif echo "$CHECK" | grep -qiE '"loggedIn"[[:space:]]*:[[:space:]]*true'; then
    echo "    token valid"
  else
    # empty output, timeout exit, network error, etc. — trust keychain.
    echo "    validation inconclusive (timeout/network/unknown) — token assumed valid, proceeding"
  fi
fi
if [[ $NEED_FRESH -eq 1 ]]; then
  echo
  echo "    → sign in as $TARGET_EMAIL in the browser that opens"
  claude setup-token
  TARGET_TOK="$(kc_read claude_code_oauth_token)"
  [[ -z "$TARGET_TOK" ]] && { echo "ERROR: setup-token produced no token"; exit 1; }
  kc_write_acct claude_code_oauth_token "$TARGET_EMAIL" "$TARGET_TOK"
  echo "    cached new token under acct=$TARGET_EMAIL"
fi

# -------- 4. keychain swap --------
echo "[4/7] keychain swap"
# preserve current acct's live token into its own banks (append-only)
if [[ "$CURRENT" != "unknown" ]]; then
  CURRENT_EMAIL="$(email_of "$CURRENT")"
  CURRENT_TOK="$(kc_read_by_acct claude_code_oauth_token "$CURRENT_EMAIL")"
  if [[ -n "$CURRENT_TOK" ]]; then
    kc_write_acct "anthropic-oauth-$CURRENT" "$ME" "$CURRENT_TOK"
  fi
fi
# set the target as the "default" (and freshen its own banks)
kc_write_acct claude_code_oauth_token "$ME" "$TARGET_TOK"
kc_write_acct "anthropic-oauth-$TARGET" "$ME" "$TARGET_TOK"
kc_write_acct claude-ai-org-id "$ME" "$(org_of "$TARGET")"
echo "    default claude_code_oauth_token → $TARGET ($TARGET_EMAIL)"
echo "    claude-ai-org-id               → $(org_of "$TARGET")"

# -------- 5. token env file + launchd setenv --------
# Keep shell startup side-effect free: zsh sources a static export file, and
# the script refreshes that file only when an account switch actually happens.
# launchctl setenv still updates GUI-launched apps for the current login session.
echo "[5/7] token env file + launchd"
TOKEN_ENV_FILE="$HOME/.openclaw/claude-token.env"
mkdir -p "$(dirname "$TOKEN_ENV_FILE")"
umask 077
{
  echo "# managed by ~/.claude/skills/switch-accounts/switch.sh"
  printf 'export CLAUDE_CODE_OAUTH_TOKEN=%q\n' "$TARGET_TOK"
} > "$TOKEN_ENV_FILE"
chmod 600 "$TOKEN_ENV_FILE" 2>/dev/null || true
echo "    wrote $TOKEN_ENV_FILE"

# launchctl setenv: makes the new token immediately visible to LaunchAgents,
# GUI apps launched via `open -a`, and anything the Dock/Finder spawns.
# This is session-scoped to the current GUI login — survives until logout.
if launchctl setenv CLAUDE_CODE_OAUTH_TOKEN "$TARGET_TOK" 2>/dev/null; then
  echo "    launchctl setenv CLAUDE_CODE_OAUTH_TOKEN (GUI/launchd session)"
else
  echo "    launchctl setenv skipped (no GUI launchd session or permission denied)"
fi
# Also update claude-ai-org-id for launchd-launched apps that read it (Desktop does).
launchctl setenv CLAUDE_AI_ORG_ID "$(org_of "$TARGET")" 2>/dev/null || true

# -------- 6. desktop bounce (opt-in only) --------
if [[ $BOUNCE_DESKTOP -eq 1 ]]; then
  # At this point --i-ran-exit-protocol has been asserted (enforced at arg-parse time).
  echo "[6/7] desktop quit + relaunch (--bounce-desktop + --i-ran-exit-protocol)"
  osascript -e 'tell application "Claude" to quit' 2>/dev/null || true
  for i in 1 2 3 4 5 6 7 8; do
    pgrep -f '/Applications/Claude.app/Contents/MacOS/Claude' >/dev/null || break
    sleep 1
  done
  pgrep -f '/Applications/Claude.app/Contents' >/dev/null && pkill -9 -f '/Applications/Claude.app/Contents' 2>/dev/null || true
  sleep 1
  [[ -d /Applications/Claude.app ]] && open -a Claude
  echo "    relaunched — use Desktop's in-app account switcher if it opens to the wrong account"
else
  if pgrep -f '/Applications/Claude.app/Contents/MacOS/Claude' >/dev/null; then
    echo "[6/7] desktop left alone (Claude Desktop is RUNNING; pass --bounce-desktop + --i-ran-exit-protocol to restart it)"
  else
    echo "[6/7] desktop already down — nothing to bounce"
  fi
fi

# -------- 7. verify --------
echo "[7/7] verify"
VERIFY="$(CLAUDE_CODE_OAUTH_TOKEN="$TARGET_TOK" claude auth status 2>&1 || true)"
echo "    claude auth status:"
echo "$VERIFY" | sed 's/^/      /'

cat <<MSG

── Done ──
  backup  : $BK
  active  : $TARGET ($(email_of "$TARGET"))
  shell   : sources ~/.openclaw/claude-token.env on new shells

Apply to THIS shell immediately (source doesn't propagate from subshells):
  export CLAUDE_CODE_OAUTH_TOKEN=\$(security find-generic-password -s claude_code_oauth_token -w)

Apply to a STUCK claude session:
  # in that session's terminal, quit claude, then:
  export CLAUDE_CODE_OAUTH_TOKEN=\$(security find-generic-password -s claude_code_oauth_token -a "$TARGET_EMAIL" -w)
  claude
MSG
