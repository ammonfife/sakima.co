# Safe mutation in a live system

Renaming, disabling, deleting and backfilling while traffic is flowing. The organising
idea: **the platform will fix the references it understands, and silently break the ones
it doesn't.** Your job is to find the second set before you start.

## Contents

1. Classify every referrer first
2. Rename with referrers rewritten in the same transaction
3. Prove liveness, not deployment
4. Before re-enabling anything, find out why it's off
5. Deprecation marking that survives contact with the next agent
6. Repair and backfill
7. Identity changes and their dependents

---

## 1. Classify every referrer first

Referrers fall into two groups and they behave completely differently:

**Tracked** — the platform knows about them and updates them automatically. Typically:
views over a renamed relation, foreign keys, dependency-tracked objects. These follow a
rename by internal id and need no action.

**Textual** — stored as text and resolved at call time. These break silently:
- function/procedure bodies
- dynamically built queries (string concatenation, ORM raw fragments)
- application and client code
- serverless/edge functions
- config, dashboards, scheduled jobs, external scripts
- anything reaching the object over an HTTP/REST layer by name

Enumerate both before touching anything. Search the running system's own catalog for
textual references, *and* search the application repo — a live system's callers are not
all inside the database.

**Worked example.** A rename of a database function looked safe: nothing declared a
dependency on it. Five other functions referenced it inside their bodies as text, two of
which served the live product's pricing path. A bare rename would have broken production
at call time, with no error until a user hit it.

---

## 2. Rename with referrers rewritten in the same transaction

There is no safe window between renaming an object and fixing its textual referrers. Do
both atomically.

Generate the new definitions **programmatically** from the current ones rather than
retyping — retyping a function body by hand to change one token is how unrelated edits
sneak in.

Guard the operation with a count assertion:

```
rewrite each referrer by substituting old name -> new name in its current definition
if rewritten_count <> expected_count: abort the whole transaction
```

A rename that "succeeded" while missing two callers is worse than one that failed loudly,
because it fails later, in production, under someone else's name.

Then assert the negative: no remaining references to the bare old name anywhere.

Watch the substitution pattern itself. A naive replace of `foo` will also hit `foo_v2`
and `mv_foo`. Anchor it — require a word boundary and, where the reference is a call, a
following `(`. Test the pattern against the known near-misses before running it.

---

## 3. Prove liveness, not deployment

"It deployed" and "HTTP 200" are both worthless as proof that a change works.

Prove it by re-running the exact operation that exercised the behaviour and asserting the
*response changed*, or by watching real traffic flow through afterward. During one rename,
the check that mattered was that **491 real matches ran through the pipeline during and
after the operation with zero failures** — not that the DDL returned success.

For deployed code, also verify the running artifact is the one you built. Deploy pipelines
skip things: check a version or content signature on the live artifact rather than
assuming a push propagated.

---

## 4. Before re-enabling anything, find out why it's off

A disabled job, flag, trigger or cron is sometimes a **containment measure**. Turning it
back on without knowing why it was turned off is how an audit becomes an incident.

Establish, in order:
1. When was it disabled, and by what change?
2. What was happening at that moment — an incident, a load problem, a bad output?
3. Is that condition still present?
4. If you re-enable it, what volume does it immediately process, and is that safe?

**Worked example.** A queue drain was found disabled with a 100k-item backlog. Re-enabling
looked obviously correct. Reading the code first showed the drain (a) ordered newest-first,
so the old backlog was unreachable regardless, (b) had a throughput ceiling *below* the
intake rate by construction, and (c) delegated identity assignment to a fuzzy text match.
Turning it on would have pushed 100k records through a path known to be wrong, and still
not cleared the queue. The flag was the least of the problems.

---

## 5. Deprecation marking that survives contact with the next agent

A prefix convention (`x_`, `zz_`, `deprecated_`) is useful but blunt: it says "dead" when
the truth is usually "dead **for this purpose**".

Say which purpose. An object may be deprecated for one lane and load-bearing in another —
mark it so, and name both lanes, or the next person deletes something the product needs.

Put the note **on the object** (a comment on the function/table itself), not only in a doc.
Doc-only deprecation is invisible at the moment of use, which is exactly when it's needed.
Include: why deprecated, what supersedes it, who still calls it, and what has to happen
before it can be dropped.

And when you discover a deprecation marker is *wrong* — the thing is live — retract it in
place with the evidence, rather than leaving a contradiction for the next reader.

---

## 6. Repair and backfill

- **Archive before you mutate.** Snapshot affected rows and the prior definitions into an
  archive location, and write the reverse operation in the *same* change set. A repair
  without a documented reversal is a bet.
- **Gate every repair on a validity check**, not just a pattern. A transformation that's
  correct for the common case can mangle the exception — verify the output form, not only
  that the input matched.
- **Recover before you discard.** Where a value is malformed, try to derive the correct one
  from the same record before deleting it. Deletion is the last resort, not the first.
- **Respect bulk guards.** Systems often reject large mutations while per-row logic is
  active, and offer a force flag. The guard is usually right — batch under the limit rather
  than forcing, because the per-row logic is often what maintains the invariants you're
  relying on.
- **Fill blanks, don't clobber.** For enrichment, prefer writing only where the target is
  empty, so a re-run can't destroy better data that arrived in between.

---

## 7. Identity changes and their dependents

The most dangerous mutation is one that changes an entity's identity — especially where
the identity is *derived* (a hash of some canonical representation), because then any
correction to that representation silently relocates the identity.

Before changing anything that feeds a derived identity:

- Enumerate every table that stores the old identity value. Derived identities are rarely
  enforced by foreign keys, so the database will not warn you.
- Repoint dependents in the **same transaction** as the identity change. Partial repointing
  produces orphans that look like missing data much later, in an unrelated report.
- Keep only *selective* attributes in the identity. Inherited descriptive attributes
  (physical properties, catalog metadata) do not distinguish one entity from another, and
  including them means every routine catalog correction moves the identity and orphans its
  dependents.
- Where a guard currently blocks an identity rewrite because the stored and computed values
  differ, understand *which* is right before choosing a direction. If the stored value is
  known-stale, blocking preserves bad data while reporting success; if the computed value is
  degraded, overwriting propagates the degradation. Measure a sample of the differences and
  classify them before deciding — and fix the generator before mass-applying its output.
