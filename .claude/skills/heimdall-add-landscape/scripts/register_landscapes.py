#!/usr/bin/env python3
"""Register the 2023 deck's row sources as engine landscapes via POST /api/landscape/add (idempotent)."""
import json, urllib.request, sys, time
B="http://127.0.0.1:8000"
G=json.load(open("defs/nov2023_groups.json"))
PICK={ "[_social media sites]":"Social Media Sites (2023)", "[_social media sites (copy)]":"Technology Providers (2023)",
 "[_INC 5000 Companies (copy)]":"Business — INC 5000 (2023)", "[_Google Ads Placements (copy)]":"Google Ads Intent Audiences (2023 labels)",
 "[_Google Ads Intent Audiences (copy)]":"Google Ads Topics (2023 labels)", "[_First Names]":"First Names (2023)",
 "[IMDB Top Movies List]":"Movies — IMDB top (2023)", "[_Law Landscape]":"Law Landscape (2023)", "[_Actors]":"Actors (2023)",
 "[Keyword Set 3]":"Banks and Finance Companies (2023)", "[_Gendered phrases]":"Family Status (2023)", "[Set 12]":"Paid Keywords — Clio (2023)",
 "[_Sports]":"Sports (2023)", "[_News outlets]":"News Outlets (2023)", "[_News outlets (copy)]":"Fake News Outlets (2023)",
 "[_discount (copy)]":"Automotive (2023)", "[Youtube Channels]":"YouTube Channels (2023)", "[_Tab Broker Landscape (copy 4)]":"Tab Website Landscape (2023)",
 "[_Tab Flow Landscape]":"Tab Flow Landscape (2023)", "[_Job Titles]":"Job Titles (2023)", "[_Russell 2000]":"Russell 2000 (2023)",
 "[_Digital Marketing Landscape]":"Digital Marketing Landscape (2023)", "[_Stock Tickers and Names keyw]":"Stock Tickers and Names (2023)"}
def clean(m):
    m=m.strip()
    if len(m)>=2 and m[0]=='"' and m[-1]=='"': m=m[1:-1]
    return m.replace('\\"','"').replace('\\#','#').strip()
for g,name in PICK.items():
    terms=[clean(x) for x in G[g]["members"]]; terms=[t for t in dict.fromkeys(terms) if t and not t.startswith("[")]
    body={"name":name,"terms":terms,"source":f"Tableau group {g}, Heimdall Nov 2023_Hopscotch.twb","queue":"--queue" in sys.argv}
    t0=time.time()
    try:
        r=json.load(urllib.request.urlopen(urllib.request.Request(B+"/api/landscape/add", data=json.dumps(body).encode(), headers={"content-type":"application/json"}), timeout=1800))
        print(f"{name:45s} n={r['n']:6d} grounded={r['n_grounded']:6d} fp={r['n_in_fingerprint']:6d} no_vol={r['n_no_volume']:5d} {time.time()-t0:.0f}s", flush=True)
    except Exception as e: print(name, "ERR", e, flush=True)
