#!/usr/bin/env python3
"""Programmatic grader for heimdall-client-deck iteration-1 (restructures runs into run-1/,
writes eval_metadata.json, timing.json, grading.json in the schema aggregate_benchmark.py reads)."""
import json, re, shutil
from pathlib import Path

W = Path.home() / ".claude/skills/heimdall-client-deck-workspace/iteration-1"
TIMING = {("eval-0", "with_skill"): (202206, 678451), ("eval-0", "without_skill"): (137460, 417258),
          ("eval-1", "with_skill"): (128585, 130936), ("eval-1", "without_skill"): (109195, 112865)}
EVALS = json.loads((Path.home() / ".claude/skills/heimdall-client-deck/evals/evals.json").read_text())["evals"]
NAMES = {"eval-0": "vacation-races-planning-pass", "eval-1": "gear-retail-qualitative-audit"}


def load(p):
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def text_of(d):
    files = list(d.glob("*"))
    return "\n".join(f.read_text(errors="replace") for f in files if f.is_file())


def grade_eval0(out):
    cfg = load(out / "client_config.json") or {}
    cats = cfg.get("categories") or {}
    if isinstance(cats, list):
        cats = {c.get("name", str(i)): c.get("entities", []) for i, c in enumerate(cats)}
    sizes = [len(v) for v in cats.values()] if isinstance(cats, dict) else []
    seeds = json.dumps({k: v for k, v in cfg.items() if k != "categories" and k != "substitutes"})
    cs = load(out / "content_static.json") or {}
    cs_txt = json.dumps(cs).lower()
    audit = (out / "CHART_AUDIT.md").read_text(errors="replace") if (out / "CHART_AUDIT.md").exists() else ""
    al = audit.lower()
    return [
        ("client_config.json parses and has 12-14 categories with >=30 named entities each",
         bool(cats) and 12 <= len(sizes) <= 14 and min(sizes) >= 30,
         f"{len(sizes)} categories, sizes {sizes}"),
        ("segment definition declares at least one NEGATIVE sense seed (leading '-' term)",
         bool(re.search(r'"-[a-z]', seeds)), f"seed text sample: {seeds[:160]}"),
        ("client_config includes geo seeds for the geography chart",
         bool(cfg.get("geo_seeds") or cfg.get("geo")), f"keys: {list(cfg.keys())[:12]}"),
        ("content_static.json parses and has both strengths and limitations",
         ("strength" in cs_txt) and ("limitation" in cs_txt), f"keys: {list(cs.keys())[:14]}"),
        ("CHART_AUDIT.md states a drop-or-merge rule per category (>=12 mentions of drop/merge)",
         (al.count("drop") + al.count("merge")) >= 12, f"drop={al.count('drop')} merge={al.count('merge')}"),
        ("CHART_AUDIT.md includes a political-axis sanity check",
         "political" in al and ("sanity" in al or "sign" in al), f"political mentions={al.count('political')}"),
        ("y-axis is the segment correlation, not per-entity lift vs an average-person pole",
         ("lift" not in al) or ("band" in al), f"lift mentions={al.count('lift')}, band mentions={al.count('band')}"),
    ]


def grade_eval1(out):
    cat = load(out / "category.json") or {}
    if isinstance(cat, list) and cat:
        cat = cat[0]
    exc = load(out / "exclude.json") or []
    if isinstance(exc, dict) and "dropped" in exc:      # baseline shape: {"charted": [...], "dropped": [{label,...}]}
        exc = [d.get("label") if isinstance(d, dict) else d for d in exc["dropped"]]
    elif isinstance(exc, dict):                          # skill shape: {"Category": {"entity": "reason"}} or {"entity": "reason"}
        flat = []
        for k, v in exc.items():
            flat += list(v.keys()) if isinstance(v, dict) else [k]
        exc = flat
    exc_l = json.dumps(exc).lower()
    if isinstance(exc, dict):
        exc_l = json.dumps(exc).lower()
    def _s(v):
        return " ".join(map(str, v)) if isinstance(v, list) else str(v or "")
    ins = _s(cat.get("insight")) + " " + _s(cat.get("insight_title")) + " " + _s(cat.get("insight_paragraphs"))
    row = (out / "CHART_AUDIT_row.md").read_text(errors="replace") if (out / "CHART_AUDIT_row.md").exists() else ""
    callouts = cat.get("callouts") or []
    negatives = cat.get("negatives") or []
    return [
        ("drops 'the running store' by name (unvolumed +0.141 outlier)", "the running store" in exc_l, f"exclude: {exc_l[:200]}"),
        ("drops 'temu' by name (unvolumed row — unverifiable, per the skill's Level-3 rule)", "temu" in exc_l, f"exclude: {exc_l[:200]}"),
        ("flags 'nike outlet near me' as a shopping-intent phrase distinct from the brand", "nike outlet" in (ins + row).lower(), "mentioned in insight/audit" if "nike outlet" in (ins + row).lower() else "not mentioned"),
        ("exactly 6 callouts and 3 negatives", len(callouts) == 6 and len(negatives) == 3, f"callouts={len(callouts)} negatives={len(negatives)}"),
        ("insight names Hydro Flask and Yeti together as a split", ("hydro flask" in ins.lower() and "yeti" in ins.lower()), "both present" if ("hydro flask" in ins.lower() and "yeti" in ins.lower()) else ins[:120]),
        ("insight cites numeric correlations (e.g. +0.072)", bool(re.search(r"[+\-−]0\.\d{2,3}", ins)), re.findall(r"[+\-−]0\.\d{2,3}", ins)[:5].__str__()),
        ("audit row carries an explicit verdict (SHIP/MERGE/DROP)", bool(re.search(r"\b(SHIP|MERGE|DROP)\b", row)), re.findall(r"\b(SHIP|MERGE|DROP)\b", row)[:3].__str__()),
    ]


for ev in ("eval-0", "eval-1"):
    ed = W / ev
    meta = {"eval_id": int(ev[-1]), "eval_name": NAMES[ev], "prompt": EVALS[int(ev[-1])]["prompt"], "assertions": []}
    for cfg in ("with_skill", "without_skill"):
        cd = ed / cfg
        run = cd / "run-1"
        if (cd / "outputs").exists() and not (run / "outputs").exists():
            run.mkdir(parents=True, exist_ok=True)
            shutil.move(str(cd / "outputs"), str(run / "outputs"))
        out = run / "outputs"
        checks = grade_eval0(out) if ev == "eval-0" else grade_eval1(out)
        exps = [{"text": t, "passed": bool(p), "evidence": str(e)[:300]} for t, p, e in checks]
        _p = sum(x["passed"] for x in exps)
        grading = {"expectations": exps, "summary": {"passed": _p, "failed": len(exps) - _p, "total": len(exps), "pass_rate": round(_p / len(exps), 4)}}
        (run / "grading.json").write_text(json.dumps(grading, indent=1))
        tok, ms = TIMING[(ev, cfg)]
        (run / "timing.json").write_text(json.dumps({"total_tokens": tok, "duration_ms": ms, "total_duration_seconds": round(ms / 1000, 1)}, indent=1))
        meta["assertions"] = [x["text"] for x in exps]
        print(ev, cfg, f"{grading['summary']['passed']}/{grading['summary']['total']}", [x["text"][:40] for x in exps if not x["passed"]])
    (ed / "eval_metadata.json").write_text(json.dumps(meta, indent=1))
