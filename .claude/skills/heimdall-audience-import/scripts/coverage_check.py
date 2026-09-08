#!/usr/bin/env python3
"""For every Tableau group (row source of a demo chart) and every audience anchor set, ask the live engine
which terms are grounded (have behavioral data). Writes defs/coverage.json + prints a table."""
import json, random, urllib.request, sys, os, time
HERE=os.path.dirname(os.path.abspath(__file__))
G=json.load(open(f"{HERE}/defs/nov2023_groups.json"))
A=json.load(open(f"{HERE}/defs/audiences_from_tableau.json"))["Heimdall Nov 2023_Hopscotch.twb"]
def clean(m):
    m=m.strip()
    if len(m)>=2 and m[0]=='"' and m[-1]=='"': m=m[1:-1]
    return m.replace('\\"','"').replace('\\#','#')
def status(terms):
    req=urllib.request.Request("http://127.0.0.1:8000/api/onboard_status", data=json.dumps({"terms":terms}).encode(), headers={"content-type":"application/json"})
    return json.load(urllib.request.urlopen(req, timeout=600))
out={"groups":{}, "audiences":{}}
random.seed(7)
SAMPLE=int(sys.argv[1]) if len(sys.argv)>1 else 1500
for name,g in sorted(G.items(), key=lambda kv:-kv[1]["n_members"]):
    mem=[clean(x) for x in g["members"] if clean(x) and not clean(x).startswith('[')]
    mem=list(dict.fromkeys(mem))
    if not mem: continue
    samp=mem if len(mem)<=SAMPLE else random.sample(mem, SAMPLE)
    t0=time.time(); r=status(samp)
    gr=sum(1 for v in r["terms"].values() if v.get("grounded")); nv=sum(1 for v in r["terms"].values() if v.get("no_volume"))
    out["groups"][name]={"caption":g["caption"],"n_members":g["n_members"],"sampled":len(samp),"grounded":gr,"no_volume":nv,
                         "pct":round(100*gr/len(samp),1),"ms":int(1000*(time.time()-t0)),
                         "cold_examples":[t for t,v in r["terms"].items() if not v.get("grounded")][:15]}
    print(f'{out["groups"][name]["pct"]:5.1f}%  {gr:5d}/{len(samp):5d}  (of {g["n_members"]:6d})  {name}  cap={g["caption"]}', flush=True)
for name,a in A.items():
    terms=[s["term"] for s in a["seeds"] if not s.get("unresolved_ref")]
    if not terms: continue
    r=status(terms); cold=[t for t,v in r["terms"].items() if not v.get("grounded")]
    out["audiences"][name]={"n":len(terms),"grounded":len(terms)-len(cold),"cold":cold}
    print(f'AUD {len(terms)-len(cold):3d}/{len(terms):3d}  {name}  cold={cold[:8]}', flush=True)
json.dump(out, open(f"{HERE}/defs/coverage.json","w"), indent=1, ensure_ascii=False)
