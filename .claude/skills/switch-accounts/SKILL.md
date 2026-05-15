---
name: switch-accounts
description: 'Toggle Claude Code login between sakima.lc@gmail.com and ammonfife@gmail.com. Handles CLI, Desktop, keychain, and ~/.zshrc. Syncs shared state append-only (never overwrite). Backs up /tmp/ artifacts. Falls back to `claude setup-token` if the target token is missing or stale. Also use when: rate-limit hit on one account and you need to switch to the other''s quota, or when Ben asks "switch account" / "use the other login" / "flip to ammonfife" / "flip to sakima".'
---

# /switch-accounts

Toggles Claude Code's active Anthropic login between Ben's two accounts:
- `sakima.lc@gmail.com` (org UUID `490d42cb-5811-4685-bad6-03d9e74d651f`)
- `ammonfife@gmail.com` (org UUID `d2d4e3ca-34da-48ab-bf95-9f3327f688d7`)

## Canonical invocation (what Claude should do)

**Claude (the assistant) MUST run `/exit-protocol` in this session BEFORE calling switch.sh.**
Then, if other active Claude sessions exist (OpenClaw agents, other CLI tabs, Desktop windows), the user must also run `/exit-protocol` in each of those before proceeding. switch.sh will detect peer CLI processes and refuse to run unless `--allow-concurrent` is set — that's the forcing function.

Canonical flow for a clean switch:

```
[ each active session ]   → run /exit-protocol
[ this session ]           → run /switch-accounts --<target>
                              ↓ (peer-detection check)
                              ↓ (keychain + zshrc work)
                              ↓ (Desktop left alone unless --bounce-desktop)
                             done
```

## How to run (command form)

```bash
# toggle (default — flips to whichever login isn't current)
~/.claude/skills/switch-accounts/switch.sh

# force target — positional
~/.claude/skills/switch-accounts/switch.sh sakima
~/.claude/skills/switch-accounts/switch.sh ammonfife

# force target — flag form (equivalent)
~/.claude/skills/switch-accounts/switch.sh --sakima
~/.claude/skills/switch-accounts/switch.sh --ammonfife
~/.claude/skills/switch-accounts/switch.sh --toggle

# behavior flags (combine freely with any target)
--dry-run                  # show the plan, change nothing
--skip-backup              # skip /tmp rescue (faster)

# OPT-IN Desktop bounce (double-gated)
--bounce-desktop           # ALSO quit + relaunch Claude Desktop
--i-ran-exit-protocol      # REQUIRED alongside --bounce-desktop; asserts state is saved

# opt-in peer override
--allow-concurrent         # proceed even when other claude CLI sessions are alive
                           # (default is to abort with a help message listing PIDs)
```

## Safety model — what's gated and why

**Default behavior: the skill leaves Claude Desktop alone.** Previously it quit + relaunched Desktop automatically; that behavior was removed 2026-04-18 because it could destroy in-progress chats in other Desktop windows. See `~/.claude/projects/-Users-benfife/memory/feedback_switch_accounts_exit_protocol.md`.

**Peer-session guard (multi-agent + same-agent multi-session):**
- Before doing anything, the script scans for other `claude` CLI processes owned by `benfife`.
- If any are found, the script aborts and prints the PIDs plus instructions to run `/exit-protocol` in each.
- Pass `--allow-concurrent` to override (useful when you know the peers are idle or on a different working dir that doesn't intersect).

**Desktop bounce guard:**
- `--bounce-desktop` alone is rejected with a message telling you to pass `--i-ran-exit-protocol` too.
- Passing both asserts you've already saved Desktop state via `/exit-protocol` (or the equivalent in-app flow).
- Without `--bounce-desktop`, Desktop is left in whatever state it's in. If it was running on the outgoing login, it stays running there until YOU bounce it when convenient.

**Why the double flag** instead of one `--force-bounce`: it's a deliberate two-key lock. `--bounce-desktop` says "I want Desktop restarted," `--i-ran-exit-protocol` says "and I've already saved state." A single flag would let muscle memory skip the save.

## Exit codes

- `0` — success (or no-op when already on target and no flags passed)
- `2` — argument parse error (bad flag, typo)
- `3` — peer sessions detected, `--allow-concurrent` not set
- `4` — `--bounce-desktop` passed without `--i-ran-exit-protocol`
- `1` — unexpected error (token fetch, keychain write, etc.)

Typical `/switch-accounts` invocations by Claude:
- `/switch-accounts` → toggle
- `/switch-accounts --sakima` → force sakima
- `/switch-accounts --ammonfife --no-desktop` → force ammonfife, leave Desktop alone
- `/switch-accounts --sakima --dry-run` → preview the plan, touch nothing

### Resync mode (same-login)

If you pass a target equal to the current login (e.g. `--sakima` while already on sakima), the script runs in **resync mode** instead of early-exiting. It re-applies every piece of derived state:

- re-freshens the `anthropic-oauth-<target>` bank from the live per-email token
- re-writes the default `claude_code_oauth_token` (acct=`$USER`) entry
- re-writes `claude-ai-org-id` to the target's org UUID
- refreshes `~/.openclaw/claude-token.env` so new shells inherit the token without a startup-time keychain call
- bounces Claude Desktop
- re-pushes Turso + appends a `[HH:MM MDT switch-accounts] resync <target>` marker to memory/today.md

Use resync when something *feels* out of sync — a shell that doesn't see the token, a Desktop stuck on a stale account, a keychain write from another tool that clobbered state. No identity change happens, so the backup-dir is `...-<target>-to-<target>` and no inter-login data transfer runs.

## What the script does (in order)

1. **Detects current login** by reading `claude_code_oauth_token` from macOS Keychain and matching it against `anthropic-oauth-sakima` / `anthropic-oauth-ammonfife`.
2. **Backs up** `/tmp/` artifacts owned by `benfife` (last 24h, scriptable/loggable extensions only, never `.lock`/`.pid`/`.sock`) to `~/clawd/backups/switch-accounts-<ts>-<from>-to-<to>/`. Also snapshots keychain entries (redacted) + `~/.zshrc` + Claude Desktop `bridge-state.json`.
3. **Append-syncs** shared state — fires `claude-sync push` in the background and appends a switch marker to `memory/today.md`. Never overwrites: memory is append-only, Turso push dedupes by content hash.
4. **Loads target token** from `anthropic-oauth-<target>` keychain entry. If missing or stale (detected via `claude auth status`), runs `claude setup-token` and caches the new token.
5. **Swaps keychain canonical** — preserves the outgoing login's token to `anthropic-oauth-<current>`, writes the target into `claude_code_oauth_token`. Also updates `claude-ai-org-id` to the target's org UUID.
6. **Writes `~/.openclaw/claude-token.env`** as a static export file for shell startup. `~/.zshenv` and interactive `~/.zshrc` source that file instead of running `security` on every shell spawn, which keeps startup side-effect free and avoids recursive CLI loops.
7. **Bounces Claude Desktop** — graceful quit via osascript, force-kill stragglers, relaunch. Desktop reloads its own per-account state from its internal keychain entries (`Claude Safe Storage`, `Claude Code-credentials-*`).
8. **Verifies** with `claude auth status` and prints the one-liner Ben can paste into an already-open terminal to apply the change without waiting for a new shell.

## What it does NOT do (by design)

- **Does not delete any keychain entry.** Every write is an upsert; previous tokens stay cached under `anthropic-oauth-<name>`.
- **Does not force-switch Claude Desktop's in-app account.** Desktop has its own account switcher UI — if it reopens to the wrong account, use that UI. (No external API to drive it.)
- **Does not touch Chrome extension auth.** The Claude Chrome extension (ID `fcoeoabgfenejglbffodgkkbkcdhcgfn`, installed in `Profile 15` + `CoinScanner`) is scoped to Chrome profiles, not to the CLI's login.
- **Does not affect already-running Claude Code sessions.** A process that's already running has the old token in memory. To switch a live session, quit that `claude` process and restart it in a terminal that has the new env var (see "Unblocking a stuck session" below).
- **Does not merge server-side claude.ai chats.** Those are per-account on Anthropic's servers and cannot be merged via API.

## Unblocking a stuck / rate-limited session

If another Claude Code session is hitting the rate limit, you can point just that session at the other account without rerunning the whole skill:

```bash
# in the terminal where the stuck session lives:
export CLAUDE_CODE_OAUTH_TOKEN=$(security find-generic-password -s anthropic-oauth-ammonfife -w)
# (or anthropic-oauth-sakima — whichever has quota left)
# quit the stuck claude process, then restart:
claude
```

The OAuth token is read once at CLI startup. Changing the keychain entry mid-session has no effect on the running process — a restart is required.

## Files this skill manages

- `~/.openclaw/claude-token.env` — static export file sourced by `~/.zshenv`/`~/.zshrc`.
- Keychain services: `claude_code_oauth_token`, `anthropic-oauth-sakima`, `anthropic-oauth-ammonfife`, `anthropic-refresh-*`, `claude-ai-org-id`. All upsert-only.
- `~/clawd/backups/switch-accounts-<ts>-<from>-to-<to>/` — per-run backup.
- `~/.claude/projects/-Users-benfife/memory/today.md` — appends a `## [HH:MM MDT switch-accounts]` marker.

## When Claude should invoke this skill

- User types `/switch-accounts` (explicit invocation).
- User says "switch accounts", "flip to the other login", "use ammonfife / sakima", "change to the other one".
- User reports a rate-limit error on the current account and the other has quota.
- Before a known multi-hour workflow, to park the current account's quota and use the other's.

## Invocation by Claude

Claude runs the script and summarizes the result:

```bash
~/.claude/skills/switch-accounts/switch.sh "${ARGS:-toggle}"
```

Then reports: before/after login, backup path, and any `claude setup-token` interactive steps the user completed.
