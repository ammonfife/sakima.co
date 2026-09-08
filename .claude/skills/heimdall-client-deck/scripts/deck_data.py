#!/usr/bin/env python3
"""Data behind every chart of a Heimdall client deck (Genomic Digital deliverable form).

Generic version of the Ragnar Races build (2026-09-05). Everything client-specific comes
from a CONFIG JSON:
    {"client": "Ragnar Races", "segment": ["audience:saved:ragnar-race-core"],
     "left": ["audience:saved:democrat"], "right": ["audience:saved:republican"],
     "categories": {"Sports": ["nfl", ...], ...},            # hand-chosen named entities
     "substitutes": {"north face": ["the north face"], ...},   # optional
     "out": "reports/<client>_deck_data.json"}
Usage:  python3 deck_data.py --config client.json   (run on the Mac; engine at :8000)

THE CHART GRAMMAR IS THE TAB BANK DECK'S (Fluid 2022, p.13-45): one curated named-entity
list per correlation category ("generated from lists of the most popular sports leagues
and teams"), every entity plotted at
    y = correlation with the client segment pole      (h(row, audience:saved:ragnar-race-core))
    x = political spectrum                             (h(row, republican) - h(row, democrat))
    size = US monthly search volume                    (master_keyword.google_volume)
with an "Average Person" reference band (the 20-row control pole the 08-22 deliverable used).
Each category page pairs that scatter with a "Key Insight" written from the named entities
that actually moved — never from the aggregate.

WHAT THIS IS NOT: an unqualified dump. Every list below was chosen by hand for the
category, every keyword is looked up as a corpus ROW (a missing row is reported, queued for
onboarding by the engine, and a substitute is tried where one is obvious), and the script
prints per-category coverage so a thin category is dropped or merged rather than charted.

    python3 scripts/ragnar_deck_data.py            -> reports/ragnar_deck_data.json (+ printed audit)

Reads: engine POST /api/batch_score (Matrix h, live cycle), master_keywords.db (ro).
Writes nothing but the report. No service touched.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

import requests

import argparse, os
HERE = Path(os.environ.get("HEIMDALL_PHASE1", os.path.expanduser(
    "~/github/ammonfife/heimdall3.0/06_scheme_L_2026/phase1")))
ENGINE = os.environ.get("HEIMDALL_ENGINE", "http://127.0.0.1:8000")
_ap = argparse.ArgumentParser(); _ap.add_argument("--config", required=True)
_ARGS = _ap.parse_args()
CFG = json.loads(Path(_ARGS.config).read_text())
SEGMENT = CFG["segment"]
AVERAGE = ['weather', 'news', 'recipes', 'walmart', 'amazon', 'facebook', 'youtube', 'google',
           'insurance', 'jobs', 'restaurants', 'netflix', 'car', 'shoes', 'coffee', 'movies',
           'music', 'hotel', 'flights', 'pizza']
LEFT, RIGHT = CFG.get("left", ["audience:saved:democrat"]), CFG.get("right", ["audience:saved:republican"])

CATEGORIES = CFG["categories"]

SUBSTITUTES = CFG.get("substitutes", {})


def batch(keywords, aud, tries=12):
    """One /api/batch_score call, surviving an engine restart mid-run (the demo is
    launchd-supervised and peers restart it; measured 2026-09-05 19:23 — the third of
    four calls landed on a booting process and the run died). Backs off up to ~6 min."""
    last = None
    for i in range(tries):
        try:
            r = requests.post(f"{ENGINE}/api/batch_score",
                              json={"keywords": keywords, "audience_terms": aud}, timeout=900)
            r.raise_for_status()
            d = r.json()
            rows = d.get("results") or d.get("scores") or []
            return {x["keyword"]: x for x in rows}
        except (requests.ConnectionError, requests.HTTPError) as e:
            last = e
            wait = min(30, 5 * (i + 1))
            print(f"  engine not answering ({type(e).__name__}); retry {i + 1}/{tries} in {wait}s", flush=True)
            time.sleep(wait)
    raise last


def volumes(keys):
    con = sqlite3.connect(f"file:{HERE / 'duckdb_index' / 'master_keywords.db'}?mode=ro", uri=True)
    out = {}
    q = "SELECT surface, google_volume FROM master_keyword WHERE surface = ? OR norm_key = ? ORDER BY google_volume DESC LIMIT 1"
    for k in keys:
        row = con.execute(q, [k, k]).fetchone()
        out[k] = int(row[1]) if row and row[1] is not None else None
    con.close()
    return out


def main() -> int:
    t0 = time.time()
    allk = sorted({k for ks in CATEGORIES.values() for k in ks} | {s for v in SUBSTITUTES.values() for s in v})
    print(f"{len(allk)} distinct keywords across {len(CATEGORIES)} categories")
    seg = batch(allk, SEGMENT)
    # The Average-Person pole is NOT scored per entity any more (it is a popularity axis, see
    # below); the average band on the charts is the middle half of all charted entities.
    avg = {}
    left = batch(allk, LEFT)
    right = batch(allk, RIGHT)
    vol = volumes(allk)

    def pick(k):
        """the keyword itself, or its first substitute that is a corpus row"""
        if seg.get(k, {}).get("h") is not None:
            return k
        for s in SUBSTITUTES.get(k, []):
            if seg.get(s, {}).get("h") is not None:
                return s
        return None

    report = {"cycle": None, "segment": SEGMENT, "average_person": AVERAGE,
              "political_axis": "h(republican) - h(democrat)", "categories": {}, "audit": {}}
    for cat, ks in CATEGORIES.items():
        pts, missing = [], []
        for k in ks:
            kk = pick(k)
            if kk is None:
                missing.append(k); continue
            s, a, l, r_ = seg[kk], avg.get(kk, {}), left.get(kk, {}), right.get(kk, {})
            if s.get("h") is None:
                missing.append(k); continue
            pol = (r_.get("h") or 0.0) - (l.get("h") or 0.0) if (r_.get("h") is not None and l.get("h") is not None) else None
            pts.append({"label": k, "row": kk, "segment_h": round(float(s["h"]), 4),
                        "average_h": round(float(a["h"]), 4) if a.get("h") is not None else None,
                        "lift": round(float(s["h"]) - float(a["h"]), 4) if a.get("h") is not None else None,
                        "political": round(float(pol), 4) if pol is not None else None,
                        "volume": vol.get(kk)})
        # y IS the segment correlation. "lift" (segment minus the Average-Person pole) is kept
        # for reference only: the 20-generic-row control is a POPULARITY axis, so subtracting it
        # per entity punishes every high-volume brand (creatine: seg +0.000, "lift" -0.315). The
        # TAB deck drew the average as a reference BAND on the segment axis; so does this deck.
        pts.sort(key=lambda p: -p["segment_h"])
        report["categories"][cat] = pts
        report["audit"][cat] = {"listed": len(ks), "charted": len(pts), "missing": missing}
        print(f"\n== {cat}: {len(pts)}/{len(ks)} charted; missing {missing}")
        for p in pts[:6]:
            print(f"   + {p['label']:<28} seg {p['segment_h']:+.4f}  pol {p['political'] if p['political'] is None else round(p['political'],3)}  vol {p['volume']}")
        for p in pts[-4:]:
            print(f"   - {p['label']:<28} seg {p['segment_h']:+.4f}  vol {p['volume']}")
    out = Path(CFG.get("out") or (HERE / "reports" / f"{CFG.get('client','client').lower().replace(' ', '_')}_deck_data.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1))
    print(f"\nwrote {out} in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
