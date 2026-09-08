#!/usr/bin/env python3
"""Register the catalog audiences in the live engine via POST /api/save_audience.

usage: register_audiences.py [--only tableau|authored|all] [--names "A,B"] [--wait]
Each save appends a revision to heimdall-audiences.duckdb and mints the pole column
(audience:saved:<slug>); cold seeds mint in the background through the serialized compose lane.
--wait polls /api/audience_namespace until every requested column is present (or 40 min)."""
import json, os, sys, time, urllib.request, urllib.parse, argparse, re

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("HEIMDALL_DEMO_URL", "http://127.0.0.1:8000")

def _wait_up(max_s=300):
    """Peers kickstart com.heimdall.demo freely (3 restarts 19:23-19:37 today); wait out a reboot."""
    t0 = time.time()
    while time.time() - t0 < max_s:
        try:
            urllib.request.urlopen(BASE + "/api/pipeline", timeout=10).read(); return True
        except Exception:
            time.sleep(5)
    return False

def post(path, body, timeout=900, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers={"content-type": "application/json"})
            return json.load(urllib.request.urlopen(req, timeout=timeout))
        except Exception as ex:
            if attempt == retries - 1: raise
            print(f"   ({type(ex).__name__} on {path}; waiting for demo, retry {attempt+1})", flush=True); _wait_up()

def get(path, timeout=120, retries=3):
    for attempt in range(retries):
        try:
            return json.load(urllib.request.urlopen(BASE + path, timeout=timeout))
        except Exception:
            if attempt == retries - 1: raise
            _wait_up()

def slug(name):   # mirrors heimdall_core/audiences.py column_name(): lowercase, non-alnum -> '-'
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="all"); ap.add_argument("--names", default="")
    ap.add_argument("--wait", action="store_true"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cat = json.load(open(f"{HERE}/defs/audience_catalog.json"))
    want = [e for e in cat if e.get("seeds")]
    if a.only != "all": want = [e for e in want if e["provenance"] == a.only]
    if a.names: keep = {n.strip() for n in a.names.split(",")}; want = [e for e in want if e["name"] in keep]
    log = {}
    for e in want:
        desc = (e.get("note") or "") + " | " + (e.get("basis") or e.get("tableau_name") or "")
        body = {"name": e["name"], "terms": e["seeds"], "description": desc[:900], "scope": "global", "source": "chart_recreation_2023"}
        if a.dry_run: print("DRY", e["name"], len(e["seeds"])); continue
        t0 = time.time()
        try:
            r = post("/api/save_audience", body)
        except Exception as ex:
            r = {"error": f"{type(ex).__name__}: {ex}"}
        r["_seconds"] = round(time.time() - t0, 1); log[e["name"]] = r
        print(f'{e["name"]:45s} {r.get("saved") and "saved" or r.get("error")} rev={r.get("revision")} minting={r.get("minting")} cold={len(r.get("cold_terms") or [])} {r["_seconds"]}s', flush=True)
    json.dump(log, open(f"{HERE}/defs/register_log.json", "w"), indent=1)
    if a.wait and not a.dry_run:
        t0 = time.time(); pending = {e["name"]: "audience:saved:" + slug(e["name"]) for e in want}
        while pending and time.time() - t0 < 2400:
            ns = get("/api/audience_namespace?origin=saved&limit=1000")
            have = {x["label"] for x in ns["audiences"]}
            for n, col in list(pending.items()):
                if col in have: print(f"  column live: {col}", flush=True); pending.pop(n)
            if pending: time.sleep(20)
        print("still pending:", list(pending.values()))

if __name__ == "__main__":
    main()
