---
name: ground-truth-audit
description: Establish what is ACTUALLY true about a live system when its documentation, its code, and its data disagree — and report it without inventing findings. Use this whenever someone asks you to check the state or progress of a running system, verify whether a documented claim still holds, investigate why a pipeline/queue/job isn't doing what it should, review what changed while they were away, or audit your own or another agent's earlier conclusions. Trigger it even when the request sounds casual ("check on the database", "is that still true?", "what happened this week?", "did that ever get fixed?", "why is X not working"), and especially when a prior report, dashboard, spec, or README is the basis for the question — those are exactly the artifacts that go stale first. Also use it before you claim a system is broken, before you name a root cause, and before you rename, disable or delete anything in a live system.
---

# Ground-truth audit

## What this is for

Someone asks you the state of a running system. Three things claim to describe it: **the documentation, the code, and the data**. In any system older than a few weeks they disagree, and the disagreements are not random — docs freeze, code accumulates dead paths, data drifts.

The job is to find out what's true. The trap is that a confident wrong answer costs far more than a slow one, because it gets written down, propagated into specs and tickets, and acted on. Most of the damage in an audit is self-inflicted: the auditor measures the wrong thing, or the right thing under the wrong conditions, then states it as fact.

So this is less about finding information than about **not believing things prematurely** — including things you concluded five minutes ago.

## The core loop

For every claim you're about to make:

1. **Name the claim precisely.** "The drain is broken" isn't a claim. "The queue backlog grew 5,962 → 101,780 while its enable flag reads false" is.
2. **Ask what would make it true — and what else could produce the same observation.** People skip the second half. It's where false findings come from.
3. **Measure that specific thing, from the most authoritative source you can reach.**
4. **State it with the measurement attached,** and an as-of time if the number moves.

If you can't complete step 3, say so. "Unverified" is a legitimate, useful output. A guess dressed as a finding is not.

## Source hierarchy — prefer what cannot be stale

When sources disagree, this ordering usually resolves it:

1. **The external system of record** — the vendor's API or page, the upstream registry, the physical artifact. Your copy of their data is a cache; caches lie.
2. **Live introspection of the running system** — catalog/schema queries, process state, effective config, real logs.
3. **The code as deployed** — which can differ from the code as committed.
4. **Generated reports** — only as good as their generation moment.
5. **Hand-written narrative** — docs, READMEs, comments, prior findings. Hypotheses to test, never evidence.

One instance worth internalizing: when your record and the vendor's disagree about the same identifier, and you check *another of your own tables* to break the tie, you've learned nothing — you consulted the same lineage twice. Go to the vendor.

## Verification traps

The specific ways a careful person still produces a false finding. Full catalog with worked examples in `references/verification-traps.md`; read it before stating a root cause. The highest-frequency ones:

**Your grep hit a comment.** Finding function B's name inside function A's body does not prove A calls B — it may sit in a comment ("logic reused from B"). Any "A calls B" claim needs the call site. This trap self-propagates: a doc written from a bad grep gets re-derived by the next person's identical bad grep.

**You measured under abnormal conditions.** A timing taken while something else saturated the system is a property of that moment, not of the thing. Check concurrent load before quoting a duration; re-measure when quiet. An order-of-magnitude gap means the quiet number is the property and the loud one is a separate finding.

**You reported a capability as damage.** "This path *can* write bad data" and "this path *has*" are different findings with different urgency. Count the bad rows before escalating. A latent flaw with zero instances is worth fixing and worth stating calmly.

**You reported absence as a blocker.** Where missing data is tolerated by design, null counts aren't findings. "Null on 94% of rows" means nothing unless something requires it non-null. Ask what breaks, not what's empty.

**You cited a frozen artifact as live.** Generated reports often embed hand-curated blocks that survive regeneration — and those blocks may *describe themselves* as derived. Check when the specific number was produced, not when the file was.

**You filtered out the evidence.** Automated commits ("auto: sync", "checkpoint", "wip") often carry the substantive work, because that's where agents and hooks deposit output. Excluding them from a progress review is how you miss the week. Census by file changed, not commit message — `scripts/git-work-census.sh`.

## Before you build, check whether it exists

An expensive, recurring failure: concluding a needed asset doesn't exist, building it, and discovering it was already built and merely unreferenced. **Unreferenced is not absent.**

Search by **shape**, not by name. The thing you need may be a file rather than a table, may sit in an artifacts/outputs directory, and may have been produced by a process nobody wired up. Grep for characteristic *content* — a column header, a delimiter, an id format — not the name you would have given it.

When you find one, record what it is, where it is, and its schema, so the next person doesn't rebuild it either.

## Before you change a live system

Renames, flag flips, deletions and backfills have one dominant failure mode: **references stored as text don't move.** Patterns in `references/safe-mutation.md`. The essentials:

- Enumerate every referrer first, separating those the platform updates automatically from those held as text — function bodies, string-built queries, client code, config, dashboards.
- Change referrers in the **same transaction** as the rename, generating new definitions programmatically rather than retyping them.
- Assert the expected referrer count and abort on mismatch. A rename that "worked" while missing two callers is worse than one that failed loudly.
- Prove liveness afterward with real traffic. A 200 and "it deployed" are both worthless as proof.
- **Before re-enabling anything, find out why it's off.** A disabled job is sometimes a containment measure, and turning it back on is the incident.

## Distinguish "not running" from "wrong when it runs"

When a pipeline isn't producing, separate these before proposing a fix — the remedies are opposite:

- **Not dispatched** — trigger, schedule or flag is off, or a debounce never expires.
- **Dispatched but failing** — it runs and errors. Find the error, not the invoker.
- **Running but starved** — correct, yet can't keep up, or its ordering means some work is never reached. *Newest-first ordering under sustained backlog makes the oldest items permanently unreachable; an oldest-unprocessed timestamp that never moves is the signature.*
- **Running, keeping up, and wrong** — throughput fine, output bad.

Quote the number that distinguishes them: dispatch timestamps, error text, in-vs-out rates, age of the oldest unprocessed item.

## Auditing your own prior conclusions

You will be wrong during the audit, repeatedly. What separates a useful audit from a damaging one is what happens next.

- **Correct in place, dated, with the reason** — not just the new answer, but why the old one looked right. That's what stops recurrence.
- **When told you're wrong, check before conceding *and* before defending.** Both reflexes generate noise. The person correcting you usually has context you lack; they're also sometimes recalling a system that has since changed.
- **Don't flip-flop.** Classified something two ways in one session? Stop and measure. A third guess is worse than a five-minute query.
- **"Are you sure?" means re-run the check,** not restate the claim.
- **Don't manufacture a stop.** Resource limits, context, "blocked" — if you're going to cite one, measure it and quote the number, or drop the sentence and continue.

## Capturing requirements while you audit

Audits surface requirements as corrections — "no, it should never do X." These are the most valuable output and the easiest to lose, because they arrive mid-investigation.

Capture them **verbatim and attributed**, and separate the rule from the instance. "Don't strip the plus sign" is an instance; "never discard tokens during normalization — they still carry signal" is the rule. Record both: the rule survives schema change, the instance proves it was real.

## Reporting

Lead with what's wrong and what's actionable, not a chronology of your investigation. Give each finding as claim + measurement + as-of.

Separate explicitly:

- **Verified** — measured, with the number
- **Unverified** — plausible, unmeasured, and what would settle it
- **Retracted** — things you said earlier *this session* that measurement disproved

That last category isn't an embarrassment to minimize. An audit that retracts nothing usually checked nothing.

Where the audit yields durable knowledge — a corrected fact, a rule the user stated, an asset nobody knew existed — write it where the next person hits it at the point of use: a comment on the object itself, the doc governing that area, the shared knowledge store. Not only in the conversation.

## Bundled resources

- `references/verification-traps.md` — full catalog of false-finding patterns, each with a worked example and the check that defeats it.
- `references/safe-mutation.md` — renaming, disabling, deleting, backfilling without orphaning referrers.
- `scripts/git-work-census.sh` — what actually changed in a repo over a window, ranked by lines per file, automated commits included.
