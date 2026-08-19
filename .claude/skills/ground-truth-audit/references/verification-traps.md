# Verification traps

Each entry: the trap, a worked example, and the check that defeats it. All examples are
real — they are mistakes made during audits, not hypotheticals.

## Contents

1. The grep that hit a comment
2. Measuring under abnormal load
3. Capability reported as damage
4. Absence reported as blockage
5. The frozen artifact that claims to be live
6. Filtering out the evidence
7. The coincidental match
8. Same-lineage corroboration
9. Sampling a distribution that isn't uniform
10. The silent success
11. Category confusion between "supplies" and "selects"

---

## 1. The grep that hit a comment

**Trap.** You search function A's source for function B's name, find it, and conclude A calls B.

**Example.** A report stated "B still exists and *wraps* A." A substring test confirmed it — B's body did contain A's name. Reading the source showed B has its own complete implementation and never invokes A; the two occurrences were comments: *"logic reused verbatim from A"* and *"exactly as A computes it"*. The two functions were independent forks with subtly different behaviour, and the whole downstream plan had been built on them being the same thing.

**Why it's nasty.** It self-propagates. The doc was probably written from this same grep, and anyone re-checking with a grep re-derives it.

**The check.** Require a call site, not a substring. Strip comments before matching, or match a call shape (`name(` preceded by a call keyword, not by a comment marker). If your language's introspection can give you a real dependency graph, prefer it.

---

## 2. Measuring under abnormal load

**Trap.** You time an operation and report the duration as a property of that operation.

**Example.** A function was reported as taking 2.8–90 seconds per call, and a performance workstream was opened on that basis. The measurements had been taken while another process was saturating the system. Re-measured on a quiet system, the same call took **104ms** — a 30× difference. The slow numbers were real observations of contention, not of the function.

**The check.** Before quoting any timing, look at concurrent activity. Re-measure at least once under different conditions. If the numbers differ by an order of magnitude, report the quiet one as the property and the loud one as a *separate* finding about contention.

---

## 3. Capability reported as damage

**Trap.** You find a code path that *can* produce bad output and report it as though it *has*.

**Example.** A queue drain delegated to a function that assigns identity via a fuzzy text match, bypassing the real matcher. That is genuinely wrong and worth fixing. The instinct was to call it a crisis. Counting the actual rows: **15 of 39,910 (0.0%)** — because a downstream trigger was overwriting the fuzzy result almost every time. Latent flaw, near-zero damage.

**The check.** Every "this is broken" gets a count. If the count is zero or tiny, say "latent — capable of X, currently N instances" and keep the urgency proportionate. This also protects you in the other direction: sometimes the count is enormous and you'd have understated it.

---

## 4. Absence reported as blockage

**Trap.** You compute null rates and present them as the problem.

**Example.** "Column populated on only 1.4% of rows" was reported as the blocker for a matching system. But the system's own rule was that missing data never blocks a match — a row simply contributes the facets it has. The null rate was therefore not a finding at all. The real defect was different: a *projection* was dropping columns that were fully populated upstream.

**The check.** For any emptiness statistic, ask "what breaks because this is empty?" If nothing requires it, it isn't a finding. Then look for the inverse — data that exists but isn't reaching the consumer. That's almost always the more actionable defect.

---

## 5. The frozen artifact that claims to be live

**Trap.** You quote a number from a generated report, assuming the whole report is generated.

**Example.** An audit page had a "full object map" whose header read *"Catalog-derived, not hand-listed: a scan of every source body."* One row showed a critical table with **zero readers**. Live introspection found two — including the function that mints the system's primary identity. The map lived inside a hand-curated block that persists across regeneration by design; only *parts* of the page were live. The header was describing an ancestor of the file, not the file.

**The check.** For generated artifacts, find the generator and check which sections it actually produces. Grep for a distinctive string from the number you're quoting: if it appears identically in both the "source" and the "output", that section is copied, not computed. Then check the as-of of the *number*, not the file.

---

## 6. Filtering out the evidence

**Trap.** Reviewing recent work, you exclude automated commits as noise.

**Example.** Reviewing six days of activity, `grep -v "auto:"` left a tidy list of feature commits. **346 of 827 commits were automated** — and they contained the substantive work: a corpus of ~814k derived records, a labelled ground-truth set, an evaluation harness, and an 855-line migration. The curated commits were the small stuff.

**Why.** Agents, hooks, and checkpoint mechanisms deposit output under generic messages. Message quality is inversely correlated with how automated the producer was, not with how important the change was.

**The check.** Census by *file changed*, not by message. Collect all commit ids in the window, aggregate line counts per file across them, rank descending. The top of that list is the week's real work regardless of what the messages say. `scripts/git-work-census.sh` does this.

---

## 7. The coincidental match

**Trap.** An identifier from one namespace happens to exist in another, so the lookup "succeeds" and returns a plausible but wrong record.

**Example.** A parser mis-attributed which vendor a scanned code belonged to, sliced it at the wrong offsets, and produced an identifier that *genuinely existed* in the wrong vendor's namespace. Enrichment then fetched real data for that wrong record. The result was **internally consistent** — every field agreed with every other field — and described a completely different item. No consistency check can catch this, because nothing is inconsistent.

**The check.** When an identifier resolves, verify it against something *outside* the identifier chain: the physical artifact, the label, a second independent attribute. And distrust cross-namespace numeric hits specifically — small integers exist everywhere. If a record's fields all agree but the item is wrong, only external corroboration will reveal it.

---

## 8. Same-lineage corroboration

**Trap.** You confirm a value by checking another source that derives from the same upstream.

**Example.** Two tables were used to cross-check an identifier. Both were populated from the same staging import, so agreement between them proved only that the import was self-consistent — which was never in question. The disagreement was with the vendor.

**The check.** Before treating agreement as corroboration, trace both sources to their upstream. If they share one, you have one witness, not two.

---

## 9. Sampling a distribution that isn't uniform

**Trap.** You sample rows, observe a pattern, and generalise.

**Example.** Cutting unresolved records by one attribute produced a clean headline ("category X is 57% unresolved, therefore a parsing bug in X"). Cutting the *same rows* by the underlying encoding split them into two unrelated root causes with different fixes — most of the X failures came from one encoding length, while a different category's failures came from an entirely different format.

**The check.** For counts and rates, use the full set — they're usually cheap. When you must sample, cut the same data by a second dimension and see whether the story survives. Pick the dimension closest to the physical/original unit rather than a derived label.

---

## 10. The silent success

**Trap.** An operation reports success while having done nothing.

**Example.** An identity-minting routine returned `ok: true` in every case, including the branch where a guard prevented it writing anything. Measured, that branch was taken on **75% of records**. Callers, dashboards and prior audits all recorded success.

**The check.** For any operation you're relying on, check the *effect*, not the return value: a row count, a changed timestamp, a state transition. Read the function's branches and ask which of them can reach the success return without doing work.

---

## 11. Category confusion between "supplies" and "selects"

**Trap.** You treat every attribute of a thing as usable for identifying that thing.

**Example.** A matcher was assessed as deficient because a catalog lacked attributes like weight, diameter, composition, designer. But those are attributes an item *inherits once identified* — the incoming records never state them, so they could never have been match inputs. Their absence blocked nothing, and the "supply gap" finding was void.

**The check.** For each attribute, ask: does the *incoming* data ever state this? If not, it's inherited, not selective, and its coverage is irrelevant to matching. This distinction also tells you what belongs in an identity key: selective attributes only. Putting inherited ones in means every catalog correction changes the identity.

---

## A general heuristic

Most of these share a shape: **an observation is consistent with your hypothesis, and you stop there.** The discipline that defeats all eleven is the same — after an observation supports your claim, spend one more step asking *what else would produce this exact observation*, and rule those out. It is cheap, it is fast, and it is the difference between an audit people can act on and one that has to be re-done.
