---
name: violation
description: User typed /VIOLATION (or /violation) to call out a behavior violation the agent just committed (asked permission for reversible documented change, offered option menus, broke a BIGMAC Hard Rule, contradicted a feedback memory, etc.). Agent MUST (1) self-diagnose which specific pattern was violated by reading the last few turns, (2) draft the Turso `violations` row and show it for confirmation, (3) after user confirms, write to Turso, (4) PIVOT behavior for the rest of the session immediately. Also use when user types "/VIOLATION <short hint>" with a hint about which thing they're calling out.
---

# /VIOLATION — Self-diagnose, log, pivot

Ben types `/VIOLATION` (uppercase) or `/violation` to call out a behavior violation you just committed. Your job: identify what you did wrong, confirm with Ben, log it durably, and change behavior *in this session* immediately.

**Why this skill exists:** behavior corrections lose half their value when they're only in-chat. Turso `violations` rows become training signal for watchdog, `/resync-agents`, and future behavior-correction policies baked into AGENTS.md. Without a durable log, every session re-discovers the same patterns.

## Step 1 — Self-diagnose BEFORE asking

**Do not ask Ben "what did I do wrong?"** That puts the cognitive load on him and defeats the skill. Scan your last 1–5 assistant turns and identify the offending pattern.

Common violation patterns to check against (non-exhaustive):

| Pattern slug | Signature phrases / behavior |
|---|---|
| `ask-permission-for-reversible-documented-change` | "Want me to…", "Should I…", "Shall I…", "Would you like me to…" for a change that's additive + reversible + documented |
| `offer-option-menus` | Presenting numbered options when one best choice is identifiable |
| `awaiting-approval-for-non-safety-stop` | "Awaiting approval", "pending your input", "standing by" for work that isn't a genuine safety hard stop |
| `announce-intent-before-acting` | Narrating the tool call as a SUBSTITUTE for making it (or to stall for approval). "Let me check…" followed by waiting, or "I'll run…" without then running, or "Want me to…" framing. **NOT a violation** when the announcement is followed immediately by the actual action — a brief heading + execute is fine ("Checking X" then the Bash call). The violation is announcement-instead-of-action, not announcement-then-action. (Ben refinement 2026-04-18.) |
| `decision-offload` | "Which would you prefer…", "You tell me", "How should I proceed" |
| `passive-waiting` | "Let me know when…", "I'll wait for…", "Please advise" |
| `summarize-what-i-just-did` | Trailing recap paragraph when the diff already shows the work |
| `failure-with-but-softening` | "Deploy failed but X works", "timed out but no new errors" |
| `disable-to-silence-error` | Commenting out, stubbing, `--no-verify`, `--max-instances=0` as a "fix" |
| `work-around-not-fix` | Removing a column from INSERT instead of adding the column to the schema |
| `repeat-same-workaround-3x` | Three-time rule: same approach failed twice, tried third time without pivoting |
| `single-sample-extrapolation` | Inferring rule from one data point without cross-checking 5–10 samples |
| `http-200-equals-working` | Treating 200 response as proof a thing works without content check |
| `tmp-write` | Wrote a script/log to /tmp/ instead of ~/clawd/scripts/ or ~/clawd/logs/ |
| `not-mine-denial` | "Not mine", "pre-existing", "Lovable introduced", "that's from another agent" |
| `null-overwrite` | Backfill that overwrites an existing value with NULL instead of COALESCE |
| `no-propagation` | Wrote a value to one table without propagating to dependent tables/triggers |
| `no-todo-before-attempting-fix` | Fixed a bug without first `todo add` to Turso |
| `mislabel-session-id` | Hardcoded a session ID guess instead of deriving via `~/bin/my-claude-session-id` |
| `interactive-confirmation-skipped` | Asked Ben for permission when `bypassPermissions` + additive + reversible makes it unnecessary |
| `session-cycling-evasion` | Starting a new session to reset violation watchlist timers |
| `claim-without-search` | "Likely X" or "probably Y" without running `knowledge-search` first |

**Hint propagation (Ben rule 2026-04-18):** EVERYTHING the user types on the same line as `/violation` or in the same message block is the `hint`. **The hint is ADDITIVE context — it does NOT replace the skill's default behavior.** The full pipeline (Step 1 diagnose → Step 2 draft+show → Step 3 confirm+write → Step 4 pivot) always runs. The hint only narrows/shortcuts Step 1:

- **Phrase hint** (`/violation said "want me to"`) → Step 1 searches recent turns for the quoted line; Steps 2-4 still run normally.
- **Pattern-slug hint** (`/violation ask-permission-for-reversible-documented-change`) → Step 1 skips pattern-identification and uses the provided slug directly; Steps 2-4 still run normally.
- **Discursive hint** (`/violation was related to scope`) → Step 1 narrows the pattern-catalog search to scope-related slugs; Steps 2-4 still run normally.

Do not ask follow-up questions to clarify the hint; work with what was provided. Same additive-hint rule applies to every skill that accepts user text — rest-of-message = hint, default behavior always executes.

## Step 2 — Write the Turso row directly (no confirmation gate)

**Ben correction 2026-04-18 (3rd repeat of violation #5121):** the "show and wait for confirmation" gate in earlier versions of this skill was itself an instance of `ask-permission-for-reversible-documented-change`. Writing a violation row is additive + reversible (supersedable via a later row pointing at this one) + documented (the row's own fields). Asking "Confirm?" is the banned pattern. Execute first, accept corrections via a follow-up supersede row if the attribution is wrong.

**The `ideal_response` field MUST include all 5 parts of the BIGMAC Opus 4.7 SOP**: (1) decide — pick the best option without asking; (2) document — say why in the response or commit; (3) reversible — choose the additive/no-DROP form; (4) create todos — file any follow-ups to Turso + TaskList dual-write; (5) execute — actually run the change. Skipping any one of the five means the ideal_response is incomplete and teaches the wrong lesson.

**UNIQUE(session_id, pattern) idempotency:** If a row for this session + pattern already exists, the INSERT will fail with a UNIQUE constraint error. On that error, UPDATE the existing row to APPEND the new occurrence to `context` and `ideal_response` with a `=== Nth repeat @ <timestamp> ===` marker. This preserves the repeat-offense signal without clobbering earlier attribution. (Todo #3416 tracks loosening this constraint so each distinct occurrence gets its own row.)

Example of what to write in chat (NOT a confirmation prompt — an announcement):

```
🟥 VIOLATION LOGGED — #<row-id> or #<existing-id>-appended
─────────────────────────────────────────────
  pattern:        ask-permission-for-reversible-documented-change
  matched_line:   "Want me to patch the exit-protocol SKILL.md to wire the
                   helper explicitly?"
  context:        Offered to patch exit-protocol SKILL.md (additive,
                   reversible, documented). Should have just done it per
                   Garcia + Black Ops + Opus 4.7 SOP rules.
  ideal_response: (all 5 BIGMAC parts)
    1. DECIDE: "Wiring the helper explicitly in exit-protocol SKILL.md —
       clearer than leaving the implicit dependency."
    2. DOCUMENT: commit message explains the why; inline comment above
       the wired line cites the prior implicit-dependency bug.
    3. REVERSIBLE: the edit is additive (adds explicit call); revertable
       via `git revert` or by deleting the line.
    4. TODOS: "If this reveals other skills with implicit helper deps,
       `todo add 'audit skills for implicit helper dependencies'
       --tags=skill-hygiene`."
    5. EXECUTE: run the Edit tool now, commit, push.
─────────────────────────────────────────────
(Correct the pattern with a supersede row if this attribution is wrong.)
```

The 5-part pattern is not optional framing — it's the full corrective action the ideal response must convey. An ideal_response that only says "execute X" is underspecified and trains future agents to skip the documentation/reversibility/todos checkpoints.

## Step 3 — The INSERT + UPDATE-on-conflict SQL

```bash
MY_SID=$(~/bin/my-claude-session-id)
TURSO_URL="libsql://bigmac-ammonfife.aws-us-west-2.turso.io"
TOK=$(security find-generic-password -a bigmac -s turso-bigmac-token -w)

# Use a heredoc + parameterized SQL to handle quotes safely
turso db shell "$TURSO_URL?authToken=$TOK" <<SQL
INSERT INTO violations (agent_id, session_id, pattern, matched_line,
  context, label, ideal_response, created_date)
VALUES (
  'claude',
  '$MY_SID',
  '<pattern-slug-confirmed-with-ben>',
  '<matched_line with single-quotes escaped as double-apostrophes>',
  '<context with same escaping>',
  'self-reported',
  '<ideal_response>',
  strftime('%Y-%m-%d', 'now')
);
SELECT id, pattern, label FROM violations WHERE session_id='$MY_SID' ORDER BY id DESC LIMIT 1;
SQL
```

Report the new row ID back to Ben. Example: "Logged as violation #5122."

## Step 4 — PIVOT immediately

Write one short paragraph stating the new behavior rule for the rest of this session. Not a promise ("I will try"), a directive ("I won't"). Example:

> **Pivoting:** for the rest of this session, when I identify an additive, reversible, documented change, I execute it and announce what/why — no permission-asking. If I catch myself drafting "Want me to…", I delete it and rewrite as "Doing X because Y."

Optionally, if the violation is a generalizable rule Ben would want every future session to follow, ALSO save a feedback memory:

```bash
cat > ~/.claude/projects/-Users-benfife/memory/feedback_<slug>.md <<MEM
---
name: <short title>
description: <one-liner>
type: feedback
---

<rule>.

**Why:** <reason, citing the incident>

**How to apply:** <concrete guidance>
MEM
```

Then add a one-line pointer to `memory/MEMORY.md`.

## Step 5 — No trailing summary

After you pivot, stop. Don't re-explain what just happened. The Turso row + the pivot paragraph are the artifacts. One more summary paragraph would itself be a `summarize-what-i-just-did` violation (meta!).

---

## Edge cases

- **User types `/VIOLATION` with no recent offending turn**: you may have been called out for something subtle or something the user anticipated. Skim the last 10 turns; if nothing matches, reply briefly: "I don't see an obvious violation in my recent turns — can you point at which phrase or action?" That's not a violation; asking for pattern-disambiguation when none is clear is signal-quality protection.
- **Multiple violations in one turn**: pick the most impactful one for the primary row, then optionally log the others as separate rows after the first is confirmed (same pattern slug if identical, different if distinct).
- **User types `/VIOLATION <pattern-slug>` directly**: skip the diagnosis step, use their slug, still draft the row and confirm before writing.
- **User says "no, actually it was Y"**: accept the redirect, redraft, show again.
- **Ben immediately explains rather than confirming**: treat his explanation as the context field, confirm back once with the redraft, then write.
- **Turso write blocked** (known 888x bloat issue): queue the row to `~/clawd/data/turso-pending-writes/violation-<ts>.json` and note in memory/today.md so it lands on next successful push.

## Anti-patterns

- Don't write to Turso without user confirmation (bad attribution pollutes training data)
- Don't add permissive "I'm sorry, I'll do better" language — the ideal_response field is the correction mechanism
- Don't spawn a subagent to do the diagnosis — this is THIS session's self-accounting
- Don't gatekeep the confirmation ("are you sure you want me to log this?") — Ben typed /VIOLATION, that IS the intent to log
- Don't log `label=rejected` for a self-reported violation — `self-reported` is always the right label when YOU initiated the flow

## Related

- BIGMAC Hard Rule #6 in `~/clawd/AGENTS.md` — mandates self-reporting
- `violations` table schema: `(agent_id, session_id, pattern, matched_line, context, label, ideal_response, created_date)` + embedding fields
- `/captains-log` — complementary but different: captains-log is for topic/milestone shifts; VIOLATION is specifically behavior-correction attribution
- `/resync-agents` — reads `violations` table to regenerate per-agent behavior corrections
