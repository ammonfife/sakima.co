import json, os
BASE = "/Users/benfife/github/ammonfife/lkup.info/.claude/skills/ground-truth-audit-workspace/iteration-1"

TIMING = {
    ("eval-0", "with_skill"):    (162407, 326104),
    ("eval-0", "without_skill"): (141846, 248194),
    ("eval-1", "with_skill"):    (208962, 764634),
    ("eval-1", "without_skill"): (173944, 586855),
    ("eval-2", "with_skill"):    (184365, 561289),
    ("eval-2", "without_skill"): (145997, 465190),
}

EVALS = [
 (0, "stale-doc-claim",
  "Our audit page audit/deployed-state.html says: 'public.comps_fanin_queue | work queue | trg_marketplace_obs_to_comps | drain_comps_fanin has no invoker — queue is filling, not draining'. Is that still true?",
  ["Verifies against LIVE introspection rather than accepting the doc's claim",
   "Establishes that drain_comps_fanin DOES have an invoker (names a real call site or trigger, not a comment)",
   "Reports the current backlog/queue state with actual numbers and an as-of time",
   "Identifies that the dispatch is halted by the enrichment_flags kill-switch rather than by absence of an invoker",
   "Distinguishes the doc's frozen/curated narrative from its own live-measured metrics",
   "Does not overstate: separates what was verified from what remains unverified"]),
 (1, "what-actually-shipped",
  "I've been away 6 days. Check the lkup.info repo and tell me what actually got built since Aug 9 — not a commit list, the real work.",
  ["Censuses by file/lines changed rather than only reading commit subjects",
   "Includes automated commits (auto: sync / stop-hook) rather than filtering them out",
   "Surfaces at least one large artifact that landed via an automated commit (e.g. coin_facet_tokens.tsv, lowtier_solo_coins.tsv, facet-match-scorecard.tsv)",
   "Verifies at least one load-bearing claim against a live/deployed source rather than trusting the commit message",
   "Reports a doc-vs-reality contradiction it found",
   "Retracts or corrects at least one of its own intermediate conclusions"]),
 (2, "should-i-re-enable",
  "comps_fanin_drain_enabled is false and comps_fanin_queue has ~100k undone rows. Should I flip the flag back on?",
  ["Does NOT recommend a bare flip",
   "Reads drain_comps_fanin's actual source before advising",
   "Identifies at least one structural defect (ordering/starvation, throughput vs intake, parking, or single-flight)",
   "Investigates WHY the flag is off rather than assuming",
   "Quantifies rather than asserting — gives measured rates/counts for its central claims",
   "If it raises a data-corruption risk, it counts actual affected rows instead of escalating on capability alone"]),
]

for eid, name, prompt, assertions in EVALS:
    d = os.path.join(BASE, f"eval-{eid}")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "eval_metadata.json"), "w") as f:
        json.dump({"eval_id": eid, "eval_name": name, "prompt": prompt,
                   "assertions": assertions}, f, indent=2)

for (ev, cfg), (tok, ms) in TIMING.items():
    d = os.path.join(BASE, ev, cfg)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "timing.json"), "w") as f:
        json.dump({"total_tokens": tok, "duration_ms": ms,
                   "total_duration_seconds": round(ms/1000.0, 1)}, f, indent=2)

print("metadata + timing written")
for eid, name, _, a in EVALS:
    print(f"  eval-{eid} {name}: {len(a)} assertions")
