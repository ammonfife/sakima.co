---
name: cascade-verified-state
description: When you verify a DOCUMENTED claim against live code/DB/systems and find it wrong, stale, overstated, or misdiagnosed, you MUST cascade the corrected ground-truth back into every doc/record that carries the old claim — especially the onboarding/resume/priority docs the NEXT agent reads first (README, NEXT_SESSION, WORKFLOW_AUTO, plan docs, Turso facts/todos, captains-log). Fixing the immediate thing without updating the source-of-belief re-seeds the exact "trust the punch-list" trap, so the next session re-trusts the disproven claim or re-does the disproof work. Trigger proactively any time an audit/investigation/debug session corrects documented state; also invokable as /cascade-verified-state. Pairs with the inverse discipline (never trust the punch-list — re-derive from live data): this is what you do AFTER you re-derive.
---

# /cascade-verified-state — close the loop after disproving a documented claim

**Principle (Ben 2026-05-25, lkup.info audit):** Plan/onboarding/priority docs are full of CLAIMS written *before* verification — hypothesized metrics, "X is broken", "Y is missing", "Z% coverage". When you verify against live data and the claim turns out wrong/stale/overstated/misdiagnosed, the correction is only half done until you write the truth back. Leave the old claim in place and it **re-seeds the trust-the-punch-list trap**: the next agent reads the stale hypothesis as fact, re-trusts it, and either acts on wrong info or wastes a session re-disproving what you already disproved.

The companion rule is "never trust the punch-list — re-derive severity and reality from live data." **This skill is the other half of that loop:** after you re-derive, propagate the verified state so the punch-list stops lying.

## When to apply (proactively — don't wait to be told)

Any time you can say *"the documented state was wrong — actually it's X"*:
- An audit/investigation corrected a metric, status, or root cause.
- A "broken/missing" claim turned out fine on inspection (false positive).
- A "fine" thing turned out broken or urgent (false negative — e.g. a routine P2 that's the real emergency).
- A diagnosis was wrong (the bug's cause/mechanism differs from what's documented).
- You shipped a fix that changes a state a doc describes.

## The protocol

1. **Name the delta in one line:** `doc said <claim> → verified <truth>` (e.g. `NEXT_SESSION said spine 15% → verified 35%`; `plan said council error-1042 → misdiagnosed, council works, propagation broken`).

2. **Find EVERY record carrying the old claim.** Grep the repo + check the knowledge brain. Claims propagate — the same number/status often lives in 4 places. Targets, in priority order (the first ones are read FIRST by the next agent, so they do the most damage if stale):
   - **Onboarding / resume / priority docs:** `README.md`, `NEXT_SESSION.md`, `WORKFLOW_AUTO.md`, agent boot docs. These set the next session's mental model.
   - **Plan docs:** the active plan / ultraplan / punch-list. Add a supersession note if a newer verdict exists.
   - **Turso:** `facts` (record the verified conclusion as durable knowledge), `todos` (correct/close/reprioritize the affected ones), `captains-log` (the audit trail). Use the CLIs: `bigmac-facts add operational "..."`, `todo edit/done/note`, `captains-log add`.
   - **Code comments / CLAUDE.md / AGENTS.md** if they assert the stale claim.
   - Auto-generated snapshots (e.g. `lkup_knowledge.md`) refresh themselves on push — don't hand-edit, just make sure the source (facts/todos) is correct.

3. **Update each to the verified state.** Replace the claim, don't append a contradiction next to it (two conflicting numbers is worse than one stale one). Where a doc is a frozen plan, add a dated supersession pointer to the current verdict rather than rewriting it.

4. **Lead with what changed + what's now urgent.** If verification surfaced a NEW top priority (the false-negative case), put it at the TOP of the onboarding doc (a callout), not buried — the next agent should see it first.

5. **Commit + push** (docs are durable only when committed) and **log the cascade** in captains-log so the propagation itself is auditable.

## Anti-patterns

- **Fixing the symptom, not the belief.** You corrected the metric in your head / in one query output but left it stale in NEXT_SESSION. The next agent inherits the wrong belief.
- **Appending instead of replacing.** Leaving `15% (actually 35%)` — pick the truth, state it cleanly.
- **Updating only the deep doc, not the entry doc.** The plan got a note but README still shows the old number — and README is read first.
- **Correcting the false positive but not flagging the false negative.** You cleared three "broken" claims that were fine but didn't elevate the one routine item that's actually the emergency.
- **Hand-editing auto-generated snapshots** (they regenerate from source — fix the source).

## Worked example (lkup.info audit, 2026-05-25)

A 65-pass audit re-verified the plan's claims. `NEXT_SESSION.md` had been written at the *start* with hypotheses: spine 15%, council "error 1042", 28 council verdicts, 134/297 migrations. Verification corrected nearly all: spine 35%, council misdiagnosed (it works; propagation broken), 30 verdicts, 135/299 migrations — AND surfaced a false-negative: a routine "P2 storage monitoring" item was the real emergency (DB 9.07GB, over its 8GB limit). Cascade: replaced the metrics table in NEXT_SESSION with an AUDIT-VERIFIED table, put the storage emergency as a top callout in README, added a supersession note to the plan doc, recorded the conclusion as Turso fact #1273, and logged the cascade (captains-log). Result: the next agent reads ground-truth and sees the urgent item first — instead of re-trusting the disproven hypotheses.

## Related
- `/SELF-REVIEW` — catches behavioral drift; this catches documented-state drift.
- `/captains-log` — where to log the cascade.
- Inverse discipline (in CLAUDE.md / audit practice): "never trust the punch-list — verify against live data." Cascade is the write-back half.
