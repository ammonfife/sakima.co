import json, glob, os
BASE = "/Users/benfife/github/ammonfife/lkup.info/.claude/skills/ground-truth-audit-workspace/iteration-1"

for p in sorted(glob.glob(os.path.join(BASE, "eval-*", "*", "grading.json"))) + \
         sorted(glob.glob(os.path.join(BASE, "eval-*", "*", "run-*", "grading.json"))):
    with open(p) as f:
        g = json.load(f)
    exps = g.get("expectations", [])
    if not exps:
        continue
    passed = sum(1 for e in exps if e.get("passed"))
    total = len(exps)
    g["summary"] = {
        "passed": passed,
        "failed": total - passed,
        "total": total,
        "pass_rate": round(passed / total, 4) if total else 0.0,
    }
    with open(p, "w") as f:
        json.dump(g, f, indent=2)
    rel = os.path.relpath(p, BASE)
    print(f"{rel:52s} {passed}/{total}")
