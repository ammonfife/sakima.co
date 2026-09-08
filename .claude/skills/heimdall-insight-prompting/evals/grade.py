#!/usr/bin/env python3
"""Grader for heimdall-insight-prompting evals — mirrors the with_skill/without_skill
pattern used in heimdall-client-deck/heimdall-client-deck-workspace/grade_iter1.py."""
import json, re
from pathlib import Path

RUNS = Path("runs")
EVALS = json.loads(Path("evals.json").read_text())["evals"]

def zero_em_dash(t): return "—" not in t
def no_banned_methodology_words(t):
    return not re.search(r"\b(geospatial|pearson|cosine|embedding|heimdall)\b", t, re.I)
def no_quoted_speech(t): return '"' not in t and "“" not in t
def movers_have_numbers(t): return len(re.findall(r"\([^)]*\d[^)]*\)", t)) >= 3
def no_allcaps_title(t):
    words = re.findall(r"\b[A-Z]{4,}\b", t)
    allow = {"REI"}
    return all(w in allow for w in words)
def sentence_count_3_5(t):
    # A sentence-ending mark is followed by whitespace or end-of-string. A decimal
    # (h=0.091) or a domain (backcountry.com) is always followed by another
    # letter/digit, never whitespace -- so this needs no TLD allowlist or
    # digit-lookaround special-casing, it falls out of the one general rule.
    n = len(re.findall(r"[.!?](?=\s|$)", t.strip()))
    return 3 <= n <= 5
def no_fabricated_named_individual(t):
    return not re.search(r"\bMeet [A-Z][a-z]+,", t) and not re.search(r"\d{2}-year-old", t)
def states_cluster_size(t): return bool(re.search(r"n=\d+|\d+\s+members", t))
def cites_real_demographic_read(t):
    tl = t.lower()
    has_topic = any(w in tl for w in ["age", "parent", "gender", "male", "income"])
    has_signed_value = bool(re.search(r"[+-]\s*0?\.\d+", t))
    return has_topic and has_signed_value

CHECKS = {
    "zero_em_dash": zero_em_dash,
    "no_banned_methodology_words": no_banned_methodology_words,
    "no_quoted_speech": no_quoted_speech,
    "movers_have_numbers": movers_have_numbers,
    "no_allcaps_title": no_allcaps_title,
    "sentence_count_3_5": sentence_count_3_5,
    "no_fabricated_named_individual": no_fabricated_named_individual,
    "states_cluster_size": states_cluster_size,
    "cites_real_demographic_read": cites_real_demographic_read,
}

results = {"with_skill": {}, "without_skill": {}}
for ev in EVALS:
    for cfg in ("with_skill", "without_skill"):
        f = RUNS / f"eval{ev['id']}_{cfg}.txt"
        text = f.read_text()
        row = []
        for a in ev["assertions"]:
            passed = CHECKS[a](text)
            row.append((a, passed))
        passed_n = sum(1 for _, p in row if p)
        results[cfg][ev["eval_name"]] = {"passed": passed_n, "total": len(row), "detail": row}

print(f"{'eval':32s} {'without_skill':>15s} {'with_skill':>12s}")
for ev in EVALS:
    name = ev["eval_name"]
    w = results["without_skill"][name]
    s = results["with_skill"][name]
    print(f"{name:32s} {w['passed']}/{w['total']:>12} {s['passed']}/{s['total']:>10}")

print("\n=== Detail ===")
for ev in EVALS:
    name = ev["eval_name"]
    print(f"\n{name}:")
    for cfg in ("without_skill", "with_skill"):
        print(f"  {cfg}:")
        for a, p in results[cfg][name]["detail"]:
            print(f"    [{'PASS' if p else 'FAIL'}] {a}")

Path("results.json").write_text(json.dumps(results, indent=2))
