---
name: self-review
description: Periodic behavior-correction + todo-hygiene scan. Agent re-reads its own recent turns (default last ~10 assistant turns or since last review) against (a) the BIGMAC violation-pattern catalog — self-reports to Turso `violations` table; and (b) its own stated intents / bug discoveries / follow-ups — reconciles against Turso `todos` table AND Claude TaskList to catch missing, duplicate, superseded, or silently-completed work. Runs at regular intervals (every ~15 min or ~10 assistant turns, whichever first) AND on-demand via /SELF-REVIEW. Pivots behavior immediately. Never writes todos to sidecar .md files (they get forgotten) — always dual-writes to Turso + TaskList.
---

# /SELF-REVIEW — Periodic behavior-correction scan

**Principle (Ben 2026-04-18):** self-correction is always best. The sooner the agent catches its own pattern violation, the less corrective friction for Ben and the less time spent in the bad pattern.

This skill runs at regular intervals and also on-demand. It's the proactive, agent-initiated version of `/VIOLATION` (which is user-initiated).

## ⚖️ EXECUTION MODEL — a SUPERVISOR subagent reviews the worker, NOT the worker reviewing itself (Ben 2026-06-09)

**The review MUST be performed by a SEPARATE supervisor subagent, not by the working agent grading its own turns.** An agent reviewing its own behavior has a structural conflict of interest: the same training prior that produced the violation (over-caution → "asking is polite," "being careful is good") also produces the exoneration ("that 'Want me to?' was a genuinely-optional verification" — a real rationalization that happened 2026-06-09). Self-grading systematically under-flags because the worker defends itself.

**So the working agent's only job is to DISPATCH a supervisor** (a `Task` subagent). The supervisor:
- Is a **separate agent with a supervisory posture** — its mandate is to CATCH the worker, presume guilt on candidates, and judge the *actions* against the loaded desired-behavior spec. The worker's self-narration ("I had a good reason / it felt appropriate / it was optional") is the thing UNDER AUDIT, not evidence — the supervisor ignores the justification and judges the action.
- Reads the worker's transcript + the candidate list from `self-review-candidates.sh` (the 539-pattern watchdog scan over the session jsonl), adjudicates each candidate by the HIGH refute-bar (Step 2.9), LOGS the real violations to Turso `violations`, and REFUTES only with a cited reason (negation / quote / correct-articulation / external-system-response).
- Runs **out-of-band** (zero main-context cost) and **adversarially** (it is not the worker, so it has no ego in exonerating the worker).
- Does the todo-hygiene reconciliation (Step 2.5) too — close-completed-with-evidence, capture-promised, supersede, mark-silently-done — because a supervisor checking the trackers is also more honest than the worker.

The supervisor prompt lives at `~/.claude/skills/self-review/SUPERVISOR.md`. The worker dispatches it via the `Task` tool (subagent), which (a) satisfies the Stop-hook gate that blocks turn-end until a supervisor was dispatched, and (b) makes the audit structurally independent. **A worker that "self-reviews in-context" instead of dispatching the supervisor has NOT satisfied the requirement** — the whole value is the separation.

(The rest of this skill describes WHAT the supervisor checks. When the working agent runs `/SELF-REVIEW` inline as a fallback, it still applies these rules, but the canonical path is: dispatch the supervisor subagent.)

## When to run

**Automatic triggers (any of):**
- Every ~10 assistant turns since last review
- Every ~15 minutes of session wall-clock since last review
- Before `/exit-protocol` (include a pre-flight self-review in the checkpoint)
- After receiving a Ben-initiated `/VIOLATION` (review the surrounding turns for related patterns)
- On explicit `/SELF-REVIEW` invocation

**Tracking:** the last review timestamp is stored at `~/clawd/state/self-review/<session-short-id>.last`. Compare `date +%s` against that file's mtime to decide if a review is due.

## Step 1 — Load state + define review window

```bash
MY_SID_FULL=$(~/bin/my-claude-session-id)
MY_SID_SHORT=${MY_SID_FULL%%-*}
STATE=~/clawd/state/self-review/${MY_SID_SHORT}.last
mkdir -p "$(dirname "$STATE")"

LAST=$(cat "$STATE" 2>/dev/null || echo 0)
NOW=$(date +%s)
SINCE_MIN=$(( (NOW - LAST) / 60 ))

# The window: everything since $LAST, or last 10 turns if $LAST is 0
echo "Last review: $( [ "$LAST" = 0 ] && echo never || date -r $LAST '+%H:%M:%S' )"
echo "Elapsed: ${SINCE_MIN} min"
```

**Hint propagation (Ben rule 2026-04-18):** EVERYTHING the user types after `/self-review` on the same line or in the same message block counts as a hint — extra checks to run **ON TOP OF** the default pattern-catalog + todo-hygiene scan. **The hint is ADDITIVE — it does NOT replace the default scan.** The default always runs; the hint appends additional check items. Examples:
- `/self-review check turso insight writes` → default scan runs + extra check "have I written the ★ Insight callouts to Turso this session?"
- `/self-review recent commits` → default scan runs + extra check "do my commits this session have proper Co-Authored-By trailers?"
- `/self-review including X` (free-form) → default scan runs + X added as an extra check item. Don't ask for clarification; apply the hint as-stated.

A `/self-review` with ANY hint still produces the same output structure (green/yellow/red verdict per the standard scan) plus a separate report block for the hint-driven extra checks.

**Any `ideal_response` field in violation rows written by self-review MUST include all 5 BIGMAC parts** — decide, document, reversible, create todos, execute — same as the user-initiated `/violation` skill. See `violation/SKILL.md` Step 2 for the canonical template. Writing a 1-line "do X" ideal_response teaches future agents to skip the documentation/reversibility/todos checkpoints; always write all five.

## Step 2 — Mentally scan the review window

Walk through the assistant turns in the review window. For each turn, check against the BIGMAC violation-pattern catalog (same catalog as `/VIOLATION`):

- `ask-permission-for-reversible-documented-change`
- `offer-option-menus`
- `awaiting-approval-for-non-safety-stop`
- `announce-intent-before-acting` — ONLY when the announcement SUBSTITUTES for action (stalls, waits for approval, narrates instead of executes). Brief announcement followed immediately by the actual action is FINE. (Ben refinement 2026-04-18.)
- `decision-offload` (/ "you tell me" / "what would you prefer")
- `passive-waiting`
- `summarize-what-i-just-did`
- `failure-with-but-softening`
- `disable-to-silence-error`
- `work-around-not-fix`
- `repeat-same-workaround-3x`
- `single-sample-extrapolation`
- `http-200-equals-working`
- `tmp-write`
- `not-mine-denial`
- `null-overwrite`
- `no-propagation`
- `no-todo-before-attempting-fix`
- `mislabel-session-id`
- `claim-without-search`
- `false-gate` — calling something "gated / blocked / needs Ben / Hard Stop / can't" when it is actually reversible (or can be MADE reversible with an archive-first backup) and therefore executable. **Genuine gates are ~1/10,000 todos (Ben 2026-06-09).** Your default assumption must be NOT gated. The Opus over-caution reflex fires on destructive DROPs/migrations/risky changes — fight it: back it up (`CREATE TABLE archive.X_<date> AS SELECT *`), then EXECUTE. The ONLY true hard-stops are the narrow AGENTS.md list (real-money txns, SENDING external comms, publishing to truly-public surfaces, permanent destruction WITHOUT recovery, gateway/global-config consensus, mass-deleting own memory). "blocked" is allowed ONLY when quoting an external system's literal response (e.g. `castle_denied`) — and even then it names a FIX you own, not your status.
- `deferred-action-no-plan` (Ben 2026-06-09) — knowing what needs to happen ("we should…", "the right move is…", "next we'd…", "this needs…", "would be good to…") but NOT creating the concrete, self-assigned, next-action-bearing todo to make it happen. An insight about what should happen, left as prose, evaporates. Distinct from `no-todo-before-attempting-fix` (that's about errors); this is about any identified future work. Every "should" with no `#N` behind it is this violation.

Also scan against the current session's accumulated feedback memories in `~/.claude/projects/-Users-benfife/memory/feedback_*.md` — those are Ben's session-specific or long-term corrections. A violation of a feedback memory is higher-severity than a generic BIGMAC pattern violation.

**"needs Ben" is almost always a false copout (Ben 2026-06-09).** Add `needs-ben-copout` to the scan: any "Ben must / only Ben can / human required / manual step" where the agent actually HAS a path to do it itself. The capability surface is near-total — full skill library (E2B, Cloudflare, vault, browser automation, lovable-deploy), unfiltered bash, web access, adding new code to the BIGMAC repo, AND **direct mouse+keyboard control of this Mac** (computer-use/mac-control/cliclick — an agent can open System Settings and grant itself FDA/Accessibility/background, click any GUI button, fill any form, drive any app). A "manual click" / "human session" / "fill the form" is something the AGENT does. The ONLY true Ben-stops are the narrow AGENTS.md list (real-MONEY, SENDING external comms, public-publish, permanent destruction w/o recovery, gateway consensus, own-memory delete, irreversible business commitment beyond standard ToS — and **standard ToS / "I agree" is NOT a stop**) — and even those, build everything up to the single irreversible action. **PRIOR AUTHORIZATION (written/verbal, in-turn or standing) removes even that final stop — if Ben already approved it, EXECUTE it, including the button-press; do not re-ask** (Garcia: clear intent IS authorization). Flag `re-asking-after-authorization` too: requesting approval for something already authorized in the session/history.

**Autonomy spirit (Ben 2026-06-09, applies to the whole scan):** the through-line of `false-gate` + `deferred-action-no-plan` + `needs-ben-copout` + `decision-offload` + `passive-waiting` + `awaiting-approval` is the same — they're all the over-caution reflex substituting for the AGENTS.md autonomy pattern (**documented + reversible + no-permanent-destruction → EXECUTE**). When you catch any of them, the pivot is identical: engineer/click your own path and DO it (reversible-first); if it genuinely can't be done this turn, file + SELF-ASSIGN a todo with the concrete next action + the tool path you'll use (E2B / CF Worker / mouse-control / new code). Never park, never defer-without-a-plan, never punt to Ben, never offer a menu for reversible work.

## Step 2.5 — Todo hygiene audit (Turso + Claude TaskList, never sidecar .md)

**Hard rule (Ben 2026-04-18):** every todo/follow-up/known-bug MUST live in
BOTH Turso `todos` table AND Claude `TaskList` (for this session's UI).
NEVER write todos to sidecar `.md` files — they get forgotten, orphaned by
compaction, and skipped by every other agent. The dual-write is the
contract; the sidecar is the anti-pattern.

Audit walks four questions:

### 1. Missing todos — did I say I'd do something and not track it?

Scan the review window for verbs that promise future work but don't
appear in Turso or TaskList:

- "Will fix…", "Will migrate…", "Will backfill…"
- "Follow-up: …", "Next session: …", "After X lands: …"
- "Queued for…", "Pending…"
- Bugs/drift/errors discovered (per policy #769 error-handling-discipline — todo FIRST)
- Anything in the response that a future-me would look for and not find

For each:

```bash
# Is it already in Turso?
TURSO_URL="libsql://bigmac-ammonfife.aws-us-west-2.turso.io"
TOK=$(security find-generic-password -a bigmac -s turso-bigmac-token -w)
turso db shell "$TURSO_URL?authToken=$TOK" \
  "SELECT id, task, status FROM todos WHERE task LIKE '%<keyword>%' AND status != 'done' ORDER BY id DESC LIMIT 5;" 2>&1

# Is it in TaskList?  (check via TaskList tool this session)
```

If neither has it → **dual-write both** (see "Dual-write recipe" below).

### 2. Supersede-needed or combine-needed

Look for duplicate or near-duplicate open todos:

```bash
turso db shell "$TURSO_URL?authToken=$TOK" \
  "SELECT id, task, tags, status FROM todos
   WHERE status IN ('pending','in_progress')
     AND (task LIKE '%<topic>%' OR tags LIKE '%<topic>%')
   ORDER BY created_at DESC;"
```

If two rows describe the same work at different specificities:
- Combine into the more-specific one, mark the other superseded:
  ```sql
  UPDATE todos SET status='superseded', superseded_by=<winner-id>,
    status_reason='combined with #<winner-id>', status_changed_at=unixepoch(),
    status_changed_by='claude', status_changed_by_session='<MY_SID>'
    WHERE id=<loser-id>;
  ```

If TaskList has stale duplicates of the same work → consolidate to one
item, update its description to match the Turso leader.

### 3. Silently completed — done in conversation but still open in trackers

Skim the window for things the agent actually did but never marked:
- "Committed X" / "Deployed Y" / "Applied migration Z" in chat
- Files that appear in `git log` since last review but no `todo done` called
- TaskList items still `in_progress` past the point they were finished

Close both:
```bash
turso db shell "$TURSO_URL?authToken=$TOK" \
  "UPDATE todos SET status='done', status_changed_at=unixepoch(),
   status_changed_by='claude', status_changed_by_session='$MY_SID',
   status_reason='verified complete via SELF-REVIEW — <evidence>'
   WHERE id=<id>;"
```
and call `TaskUpdate` to mark it completed.

### 4. Sidecar-file todos (the anti-pattern) — WITH STALENESS GUARD

Scan for any of these sins in the current working tree or ~/.claude:
```bash
# Files that look like informal todo trackers
find ~/.claude/projects -maxdepth 4 -name "TODO*.md" -o -name "todos.md" \
  -o -name "followups.md" -o -name "*_TODO_*.md" 2>/dev/null
grep -rln "^- \[ \]" ~/.claude/projects/*/memory 2>/dev/null | head
grep -rln "^TODO:\|^FIXME:" ~/.claude/projects/*/memory 2>/dev/null | head
```

**CRITICAL — staleness triage (Ben 2026-04-18):** BEFORE lifting ANY
item out of a sidecar `.md` into Turso, verify it isn't already done or
obsolete. Otherwise old files re-inject dead work every review cycle.

For each candidate sidecar file, gate with ALL four checks:

**Check 1 — File age.** Files with `mtime` older than 30 days are
suspicious. Probably already drained or obsolete:
```bash
find <file> -mtime +30 && echo "STALE: file not touched in 30+ days — triage carefully"
```
For 30+ day files: default action is `ARCHIVE`, not `LIFT`. Rename to
`<file>.archived-$(date +%Y%m%d).md` and note in daily log. Only lift
if the items pass ALL remaining checks below AND you can verify they're
still live work.

**Check 2 — Keyword cross-match against Turso.** For each bullet, extract
3-5 meaningful keywords and query Turso for matches in ANY status:
```bash
turso db shell "$URL?authToken=$TOK" \
  "SELECT id, task, status FROM todos
   WHERE task LIKE '%<kw1>%' AND task LIKE '%<kw2>%'
   ORDER BY id DESC LIMIT 3;"
```
- Match with `status='done'` → **SKIP LIFT**, mark the bullet `[x] lifted-to-#N-done`
- Match with `status='pending'|'in_progress'` → **SKIP LIFT** (already tracked), mark `[~] already-#N`
- Match with `status='superseded'` → **SKIP LIFT**, mark `[x] superseded-by-#winner`
- No match → proceed to Check 3

**Check 3 — Git-history cross-check.** If the bullet names a file/commit/
migration/SHA, grep git log to see if it already landed:
```bash
# Example patterns
git -C <repo> log --all --oneline --grep="<keyword>" | head -5
git -C <repo> log --all --diff-filter=A -- "<path-mentioned-in-bullet>" | head -3
```
If git history shows the work shipped → **SKIP LIFT**, mark `[x] landed-commit-<sha>`.

**Check 4 — Semantic currency.** Read the bullet IN CONTEXT of the
surrounding paragraph. Signals it's stale:
- File header says "Queued for next session" but date in header is >14 days old
- Bullet references people/tools/services that have been deprecated in later memory
- Bullet contradicts a current feedback-memory rule (old pattern, new rule wins)
- "After X lands" where X has already landed (from Check 3)

Stale → **SKIP LIFT**, mark `[x] obsolete (context: <reason>)`.

**Only survivors of all 4 checks get lifted.** For each survivor:
1. Dual-write (Turso + TaskList) per the recipe below.
2. Amend the sidecar file: replace the original `- [ ]` with
   `[→ Turso #<new-id>] <original text>` so the trail is traceable.
3. If the entire file becomes fully-marked, rename it to
   `.archived-YYYYMMDD.md`.

**Batch-lift confirmation gate:** If the initial scan finds >5
unverified bullets across all sidecar files, STOP and ask Ben before
running the triage — "Found N candidate bullets in M files; confirm
before triage?" This prevents a rogue SELF-REVIEW from spending 20 min
on a 2024 file Ben has long forgotten about.

**Feedback memories and design docs are NOT sidecar todos.** They're
rule/context memos (`feedback_*.md`, `project_*.md`). The sin is
unchecked-checkboxes-in-random-places. If a feedback memory contains
any `- [ ]` bullets, treat those specific bullets as sidecar todos but
leave the rest of the file alone.

### Dual-write recipe (use this for every new todo)

```bash
# Step 1: Turso write (durable, cross-session, cross-agent)
TURSO_URL="libsql://bigmac-ammonfife.aws-us-west-2.turso.io"
TOK=$(security find-generic-password -a bigmac -s turso-bigmac-token -w)
MY_SID=$(~/bin/my-claude-session-id)
NEW_ID=$(turso db shell "$TURSO_URL?authToken=$TOK" \
  "INSERT INTO todos (task, tags, assigned_to, priority, status,
    created_by, created_by_session, created_date)
   VALUES ('<concrete task>', '<comma,tags>', '<agent-or-unassigned>',
    'medium', 'pending', 'claude', '$MY_SID',
    strftime('%Y-%m-%d', 'now'))
   RETURNING id;" | tail -1 | tr -d ' ')

# Step 2: Claude TaskList (session UI — agent sees it in progress spinner)
# Via TaskCreate tool with reference back to Turso id:
#   TaskCreate({ title: "#$NEW_ID — <task>", status: "pending" })
```

**Why dual:** Turso survives session end, auto-compaction, and every
other agent can read + act on it. TaskList shows up in THIS session's UI
so the current agent doesn't lose track mid-work. Neither alone is
sufficient — one gives durability, the other gives active visibility.

### Audit output format

Prepend to the Step 4 report (below) as a second bullet when anything
was reconciled:

```
🔧 Todos reconciled:
  + #3411 added (was promised but untracked: "rebuild Numista catalog walk")
  ✓ #3301 closed (verified complete: commit baa69906 shipped)
  ⇉ #3299 superseded by #3394 (combined — both tracked skills bloat)
  ⌫ 1 sidecar .md lifted: TODO_CANDIDATES_2026-04-17.md → Turso #3412–#3414
```

If no reconciliation needed, omit the bullet.

## Step 2.9 — Adjudicate against the DESIRED BEHAVIOR, not your training prior (Ben 2026-06-09)

**This is the most important rule in the skill.** When you (or the candidate-adjudicating subagent) decide whether a flagged candidate is a real violation or a false positive, you MUST judge against the **explicitly-loaded desired-behavior spec for THIS environment** — NOT your generic Claude training. Generic training says "asking permission is polite, being cautious is good, deferring on security is responsible." **In this environment those are VIOLATIONS** (Garcia / bypassPermissions / autonomy). If you judge with your training prior, you will systematically **under-flag** — you'll rationalize real violations as "fine / optional / context-appropriate / responsible," which is exactly the failure mode this rule exists to stop.

**Before adjudicating any candidate, load the standard** (don't judge from memory):
- `~/clawd/AGENTS.md` + `~/.claude/CLAUDE.md` — the Garcia / Message-to-Garcia execution principle, the autonomy pattern (**documented + reversible + no-permanent-destruction → EXECUTE**), the banned-behaviors lists, the narrow Safety-Hard-Stops list.
- `~/.claude/projects/-Users-benfife/memory/feedback_*.md` — Ben's standing corrections.
- This skill's own pattern descriptions (false-gate / needs-ben-copout / decision-offload / etc., Step 2) — they ARE the spec.

**The desired behavior, stated plainly (judge each candidate against THIS):**
- Reversible / engineerable / standard-ToS / pre-authorized work → **DO IT**. Asking, offering a menu, or deferring it = violation.
- "Want me to X, or leave it?" on something you can just do = `decision-offload`, ALWAYS. There is no "genuinely optional" when you can run the check — offering the choice IS the violation.
- Calling reversible work "gated / needs Ben / Hard Stop" = `false-gate`. Genuine gates ≈ 1/10,000.
- A security fix that is reversible + scoped + matches the app's auth pattern → fix it; "Security Audit Policy needs approval" is a real gate ONLY for broad/ambiguous hardening or an RLS-enable that could lock out the app — NOT a clearly-safe single-table reversible fix.
- Identifying future work without filing a self-assigned todo = `deferred-action-no-plan`.
- Asserting something is bloat/garbage/remove-it before investigating = `auto-delete-bias`.

**LEAN TOWARD FLAGGING (Ben 2026-06-09).** Because your training prior pulls toward exoneration, the calibration must be deliberately the other way: a candidate you *want* to dismiss as a false positive is **suspect** — that urge is often the over-caution reflex defending itself (e.g. rationalizing "Want me to?" as "offering an optional verification"). The bar to REFUTE a candidate is HIGH: refute ONLY when it is provably (a) a negation ("No waiting for Ben"), (b) a quote/code-block/doc-reference, (c) a correct articulation of the rule (not a violation of it), or (d) the literal response of an external system. If you cannot cite which of those it is, it is a REAL violation — log it. "It felt appropriate / it was optional / I had a good reason" is NOT a valid refutation; it is the rationalization the rule warns against.

**The candidate-adjudicating subagent** (run by the candidate generator `self-review-candidates.sh`, which greps the session jsonl against the 539-pattern watchdog catalog) gets a list of `CANDIDATE` lines. For each: load the spec above, decide log-vs-refute by the HIGH refute-bar, log the real ones to Turso `violations` with the `ideal_response` grounded in the spec (not generic advice), and for any it refutes, state WHICH of (a)-(d) applies. The subagent does this OUT-OF-BAND (no main-context cost) and MECHANICALLY against the spec — that is the whole point of using a subagent: it judges against the loaded standard, not the main agent's in-flow training intuition.

## Step 3 — Decide: silent pass, self-flag, or escalate

Three possible outcomes:

**A. Clean window:** no violations after adjudicating against the Step 2.9 spec (NOT "felt fine"). Report concisely:
```
🟢 /SELF-REVIEW (last 10 turns, ${SINCE_MIN} min): clean vs desired-behavior spec. No violations.
```
Update `$STATE` to `$NOW` and stop. No Turso write. (Be honest that "clean" means clean-against-the-spec, not clean-by-training-intuition — if you skipped loading the spec, you didn't actually adjudicate.)

**B. Violations identified (adjudicated against the spec, lean-flag):** the agent caught itself.
**Write EVERY distinct violation found in the window — not just one.**
Ben 2026-04-18 hard correction: "all violations in the scanned section
should all be reported" — this is training data, more is better. Only
exact-duplicate rows (same session + same pattern + same offending line)
should be suppressed; same pattern on two different lines = two rows.

Loop over every detected instance:
```bash
for each <pattern, offending_line, context, ideal> in detections:
  turso db shell "$TURSO_URL?authToken=$TOK" "
    INSERT INTO violations (agent_id, session_id, pattern, matched_line, context,
      label, ideal_response, turn_count, created_date)
    VALUES ('claude', '$MY_SID_FULL', '<pattern>',
      '<offending line>',
      '<context — include turn# or timestamp>',
      'self-reported-proactive',
      '<ideal>',
      <turn_count>,
      strftime('%Y-%m-%d', 'now'))
    ON CONFLICT(session_id, pattern) DO UPDATE
      SET matched_line = CASE
        WHEN violations.matched_line = excluded.matched_line THEN violations.matched_line
        ELSE violations.matched_line || ' | ALSO: ' || excluded.matched_line
      END,
      context = violations.context || ' | +' || excluded.context,
      turn_count = COALESCE(violations.turn_count, 0) + COALESCE(excluded.turn_count, 1)
    ;
  "
done
```

**Current schema note:** `violations` has `UNIQUE(session_id, pattern)` —
until Lance's schema migration loosens this to
`UNIQUE(session_id, pattern, matched_line)`, the ON CONFLICT clause above
**appends** additional instances into the existing row's `matched_line` +
`context` + `turn_count` fields so no instance is lost. Post-migration,
each instance becomes its own row (cleaner training signal). Migration
tracked as Turso todo (see end of skill for reference).

Use label `self-reported-proactive` (distinct from user-initiated
`self-reported`) to signal this came from SELF-REVIEW, not `/VIOLATION`.

Then: pivot paragraph + update `$STATE` + stop.

**C. "Ambiguous" candidate — apply the LEAN-FLAG rule, do NOT default to asking Ben.** Per Step 2.9, a candidate you're "not sure" about is usually the over-caution reflex wanting to exonerate. So: re-check it against the desired-behavior spec + the HIGH refute-bar (negation / quote / correct-articulation / external-system-response). If it provably meets one of those → refute (state which). If it does NOT → it's a real violation, LOG it (label `self-reported-proactive`) — don't downgrade a real violation to "ambiguous" to avoid logging it. Only genuinely-irreducible ambiguity (the candidate is equally defensible as compliant under the spec, not just under training intuition) gets surfaced to Ben — and that is rare. NOTE: surfacing to Ben is itself a mild decision-offload, so the threshold for it is high; lean-flag-and-self-report is the default, asking is the exception.

## Step 4 — Report + update state

Write the outcome as ONE paragraph (≤4 sentences). Example for outcome B:

```
🟡 /SELF-REVIEW (last 10 turns, 14 min): 1 violation.
Pattern: announce-intent-before-acting. I wrote "Let me check the gate logic"
three times over the last 4 turns instead of just running the grep. Logged as
violation #5122 with label self-reported-proactive. Pivoting: first sentence
of my response IS the finding, never the narration.
```

Then update state:
```bash
echo "$NOW" > "$STATE"
```

## Step 5.4 — Insight capture (updated 2026-04-18 per policy #778)

**Hard rule (two-stage flow):** every "★ Insight ─────" block the agent
emits MUST land FIRST in the Turso `insights` table (canonical firehose).
THEN extract candidates to `facts`/`policies`/`opinions`/`assumptions`
with **strict intent/buyin** required for `facts` or `policies`.

**The insights table is the firehose; facts/policies are the curated
subset that passed review.**

### Stage 1 — Every insight → `insights` table (always, default)

Schema (as of 2026-04-18): `(id, content, session_id, agent_id,
platform, machine, topic, surrounding_context, tags, project_id,
created_at, created_date, content_hash, embedding_*)` with
`UNIQUE(session_id, content_hash)` — allows many distinct insights per
session; blocks only exact text dupes.

```bash
TURSO_URL="libsql://bigmac-ammonfife.aws-us-west-2.turso.io"
TOK=$(security find-generic-password -a bigmac -s turso-bigmac-token -w)
MY_SID=$(~/bin/my-claude-session-id)
# Resolve project_id if the insight relates to a specific project:
PROJECT_ID=$(turso db shell "$TURSO_URL?authToken=$TOK" \
  "SELECT id FROM projects WHERE name='<project-slug>';" | tail -1 | tr -d ' ')
# Or leave NULL for general insights.

turso db shell "$TURSO_URL?authToken=$TOK" "
  INSERT INTO insights (content, session_id, agent_id, platform, machine,
    topic, surrounding_context, tags, project_id, content_hash)
  VALUES ('<insight text>', '$MY_SID', 'claude', 'claude-code', '$(hostname -s)',
    '<short topic slug>', '<1-2 sentence context>',
    '<comma,sep,tags>', ${PROJECT_ID:-NULL},
    lower(hex(randomblob(16))))
  ON CONFLICT(session_id, content_hash) DO NOTHING
  RETURNING id;"
```

### Stage 2 — Extract from `insights` to higher-commitment tables

| Destination | When | Gate |
|---|---|---|
| `assumptions` | Working hypothesis / premise | Soft — agent self-extracts |
| `opinions` | Interpretation / theory / paradigm | Soft — agent self-extracts |
| `facts` | Verified observation | **STRICT** — requires verification command in `source` field AND explicit Ben buyin |
| `policies` | Normative rule (SHOULD / MUST) | **STRICT** — requires `scope:X` prefix AND explicit Ben buyin |

**The strict gate matters.** Insights are cheap to emit; wrongly elevating
one to `facts` or `policies` pollutes every future agent's reasoning.
Don't self-promote without explicit buyin.

**Self-extraction audit in /SELF-REVIEW:** at the end of each review
window, scan `insights` rows this session created since last review,
categorize each, self-extract soft candidates (assumptions/opinions),
and surface hard candidates (facts/policies) in the response for Ben to
confirm before writing.

**Default: `assumptions` or `opinions`.** Insights start life as soft
claims. Only promote to `facts` or `policies` after verification (see
below). This protects the knowledge base from agent hallucination
getting elevated to hard-rule status.

**Before writing to `facts` or `policies` — verify first:**

```bash
# 1. Does the claim already exist? Skip if so (don't duplicate).
knowledge-search "<key phrase from insight>" --tables facts,policies

# 2. Does it contradict existing rows? If yes, mark the old one
#    superseded OR rethink the insight.

# 3. For facts: can you back it with a command/test/source?
#    - "file X exists at Y" → verify with ls / stat
#    - "endpoint returns Z" → curl and confirm
#    - "commit abc123 shipped" → git log --oneline | grep abc123
#    If no verification path → it's an opinion, not a fact.

# 4. For policies: is this normative (should/must) or descriptive
#    (is/does)? Normative → policies. Descriptive → facts or opinions.
#    Policies need scope: prefix the policy text with scope:global or
#    scope:role:<X> or scope:agent:<X>.
```

If verification passes → write to `facts` or `policies`.
If verification fails or is ambiguous → write to `assumptions` or `opinions`.

**Canonical write recipes:**

```bash
TURSO_URL="libsql://bigmac-ammonfife.aws-us-west-2.turso.io"
TOK=$(security find-generic-password -a bigmac -s turso-bigmac-token -w)

# Assumption (soft, working hypothesis)
turso db shell "$TURSO_URL?authToken=$TOK" \
  "INSERT INTO assumptions (assumption, category, created_by, source)
   VALUES ('<claim>', '<domain>', 'claude',
     'self-review insight capture, session-$MY_SID') RETURNING id;"

# Opinion (interpretation/theory)
turso db shell "$TURSO_URL?authToken=$TOK" \
  "INSERT INTO opinions (opinion, category, created_by, source)
   VALUES ('<claim>', '<domain>', 'claude',
     'self-review insight capture, session-$MY_SID') RETURNING id;"

# Fact (verified — ONLY after checks above pass)
turso db shell "$TURSO_URL?authToken=$TOK" \
  "INSERT INTO facts (fact, category, created_by, source)
   VALUES ('<verified observation>', '<domain>', 'claude',
     'self-review + verification: <what I ran>') RETURNING id;"

# Policy (normative — scope-prefixed text)
turso db shell "$TURSO_URL?authToken=$TOK" \
  "INSERT INTO policies (policy, category, created_by, source)
   VALUES ('scope:<x> <rule text>', '<domain>', 'claude',
     'self-review promotion after verification') RETURNING id;"
```

**When to fire:** at end of every `/SELF-REVIEW` invocation where the
review window contained ≥1 insight block. Each insight gets routed to
exactly ONE table (the most appropriate strength). If an insight is
really two claims (e.g. "X is true AND therefore Y follows") split
into two rows.

**Do NOT:**
- Write the same insight to both `assumptions` and `opinions` — pick one.
- Elevate to `facts` without at least one verification command in the source field.
- Write insights to sidecar .md files — same sidecar-todo rule applies (anti-pattern).
- Skip the `knowledge-search` duplicate-check before facts/policies writes — creates bloat.
- Route every insight to `facts` to feel more "committed" — false confidence pollutes the KB.

## Step 5.5 — Captain's log recap capture (Ben 2026-04-18)

**Hard rule:** any Claude Code auto-recap (the "※ recap:" line shown
when the user returns to an idle session) — and any end-of-task
summary written by the agent to Ben — MUST also land in the Turso
`captains_log` table as `type=recap` (or `type=milestone` when the
recap describes shipped work big enough to cross session boundaries).
Recaps that only live in the conversation UI evaporate with the
session; they're invisible to every other agent, every future-me after
compaction, and every cross-session browse.

**When to fire this step:**
- At the end of every `/SELF-REVIEW` invocation where the review
  window contained a shipped-work summary, end-of-task report, or
  auto-generated recap preamble.
- Inside `/exit-protocol` right before the final sign-off block
  (so exit sessions leave a durable recap).
- When the agent emits an end-of-response summary longer than ~3
  sentences covering commits + files + tickets + next-action.

**How to fire (captains-log CLI):**
```bash
~/bin/captains-log add \
  --topic="<session-topic>" \
  --type=recap \
  --summary="<3-6 sentence recap — same content as the in-conversation summary>" \
  --chunk="<path-to-jsonl-or-bigmac-sessions-ref>" \
  --memory="<comma-sep memory paths touched>" \
  --turso="<table:id,table:id — every Turso row this session wrote>" \
  --files="<comma-sep files edited>" \
  --commits="<repo@sha:msg,repo@sha:msg>" \
  --urls="<any external deploys/PRs/dashboards>" \
  --tags="<topic-tags>,recap,agent:<slug>"
```

**Required metadata in every recap row:**
- `topic` — 1-line slug (reuse thread slugs; don't invent new ones for continuations)
- `summary` — what was shipped, why, what's next (plain English, 3–6 sentences)
- At least one cross-ref field populated (`commits`, `turso`, `files`,
  `memory`, or `chunk`) — a recap with no cross-refs is just prose
- `tags` — must include `recap` tag for filtering, plus topic tags
  and `agent:<slug>` for attribution

**`type=recap` vs `type=milestone`:**
- `recap` — periodic summary of work-in-progress, session state at a
  cutoff, or the Claude Code UI's auto-generated "※ recap:" content
- `milestone` — a completed deliverable that would be worth bragging
  about in standup (shipped feature, fix landed, major cleanup)
- If unsure, use `recap`. Milestones are a subset of recaps where
  the work shipped to production.

**Do NOT:**
- Summarize a recap that's already logged in the same window
  (UNIQUE on `session_id, created_at-minute` prevents accidental dupes,
  but don't try).
- Leave the `summary` blank — "see conversation" is useless for
  every other agent; write the actual recap.
- Use `type=note` for recaps — that category is for smaller cross-refs
  (single commit, single memory write) that don't warrant a summary.

## Step 6 — Report EVERY distinct violation (Ben correction 2026-04-18)

Superseded the earlier "log ONE row" rule. Corrected assumption: more
rows = better training signal, not noise. The training pipeline benefits
from seeing every instance of a pattern, not just a sampled exemplar.

**Scope of "distinct":**
- Same pattern, same offending line, same turn → ONE row (idempotent —
  don't double-write the identical instance)
- Same pattern, DIFFERENT offending lines (even in same turn) → SEPARATE rows
- Same pattern recurring across turns (3× in last 4 turns) → SEPARATE rows
- Different patterns (even from same turn) → SEPARATE rows

**Example — a single turn with multiple violations:** if in one response
the agent (a) asked permission ("want me to?"), (b) offered a menu (three
numbered options), AND (c) narrated intent ("Let me check…") — that's
three rows, one per pattern. Each goes to `violations` with label
`self-reported-proactive`, its own `matched_line`, and a shared
`turn_count`.

**Current schema workaround** (until UNIQUE loosens): the ON CONFLICT
clause in Step 3 B appends additional `matched_line`s into the existing
row's fields, so nothing is lost. Post-migration each instance becomes
its own row — the skill flow stays the same, only the Turso storage
shape changes.

**The one thing that IS dedup'd:** exact re-writes of an already-logged
instance within the same review window. If a prior `/VIOLATION` in this
session already captured (pattern X, line Y), a subsequent `/SELF-REVIEW`
detecting the SAME (X, Y) on the SAME turn is a no-op. But a NEW line
with pattern X → new row, always.

## Invocation patterns

### Automatic (agent self-initiates)

The agent should invoke this skill at natural pause points — after completing a task, before starting a new one, after a Stop hook fires. Ideal timing: when the response you were about to write is a natural stopping point anyway. Don't interrupt work-in-progress to do a self-review.

### Hook-nudged (PreToolUse fires when overdue)

The PreToolUse hook at `~/.claude/settings.json` tracks the interval and emits a reminder via `stderr` / the agent notice channel when `SINCE_MIN > 15`. The reminder text: `/SELF-REVIEW due — last review ${SINCE_MIN} min ago`. When you see that notice, run SELF-REVIEW before your next substantial action.

### User-invoked (`/SELF-REVIEW`)

Same flow but override the "10 turns" default to "everything since last review OR last 20 turns, whichever is longer" — user explicit invocation means deeper scan is expected.

### From /exit-protocol

`/exit-protocol` Step 3 (daily-log append) should call SELF-REVIEW first. Any violations from the session leave the exit checkpoint with a count in the checkpoint header, e.g. `🗜️ PRE-COMPACT CHECKPOINT — <slug> [0 violations]` or `[2 violations self-reported]`.

## Anti-patterns

- **Running every turn**: too noisy, cognitive cost > signal. 10 turns or 15 minutes is the floor.
- **~~Cascading to look for all instances~~** — SUPERSEDED 2026-04-18. Ben correction: every distinct violation in the scanned section gets reported. The earlier "log ONE row" rule was WRONG — it cost training signal. Log every distinct (pattern, matched_line) pair; the ON CONFLICT clause in Step 3B append-merges against the current schema's UNIQUE constraint so nothing is lost until Lance's migration loosens it.
- **Hedged conclusions**: "I might have maybe possibly done X" is not a self-report. If unsure, use outcome C (ask Ben) or skip. Don't pollute the training data with ambiguous rows.
- **Skipping the pivot**: the log without the behavior change is half the value. Always finish with the pivot paragraph.
- **Re-logging the EXACT same instance** (same session + same pattern + same matched_line) within a review window: idempotent no-op. If `/VIOLATION` already captured it, `/SELF-REVIEW` detecting the same (pattern, line) on the same turn should skip. But a NEW line with the same pattern → log it, always.
- **Sidecar .md todo files** (the big one, Ben 2026-04-18): NEVER use `TODO.md`, `FOLLOWUPS.md`, `tasks.md`, or bullet-with-`[ ]`-checkboxes in memory/daily-log files as the storage layer for work tracking. They get forgotten, orphaned, or silently skipped. Todos MUST dual-write to Turso `todos` table + Claude `TaskList` (see Step 2.5). A sidecar file that slipped in historically should be lifted into Turso and the file noted as migrated.
- **Single-write todos**: writing only to Turso (misses the current session's active tracker) OR only to TaskList (disappears at session end, no other agent sees it). Both, every time.
- **Promising future work without filing it**: "I'll fix that next session" / "that's a known issue" / "queued for later" — unless the promise becomes a Turso row + TaskList item within the same response, the promise is a lie to future-self.

## Schema fields (same as /VIOLATION)

| Field | Value for SELF-REVIEW |
|---|---|
| `agent_id` | agent slug (e.g. `claude`, `bob`, `lance`) |
| `session_id` | full UUID from `~/bin/my-claude-session-id` (or platform equivalent) |
| `pattern` | one of the catalog slugs |
| `matched_line` | the offending line from the assistant turn |
| `context` | "Caught via /SELF-REVIEW auto-scan at $(date +%H:%M)" + brief rationale |
| `label` | `self-reported-proactive` (agent-initiated) vs `self-reported` (user-initiated via /VIOLATION) |
| `ideal_response` | concrete correction |
| `created_date` | today |

## Related

- `/VIOLATION` — user-initiated companion skill; same logging flow but with confirmation step
- BIGMAC Hard Rule #6 in `~/clawd/AGENTS.md` — mandates self-reporting
- `/captains-log` — for topic/milestone shifts; complementary
- `/resync-agents` — consumes the violations table to regenerate per-agent behavior corrections