#!/usr/bin/env python3
"""Extract Tableau groups/sets (named member lists) from a .twb — these are the ROW SOURCES of the demo charts
(e.g. '_social media sites', 'Youtube Channels', 'Influencer List', '_Sports', 'Fake News').
Streams in 64MB chunks; <group> elements can be 100k+ members so we split on '<group ' and read to '</group>'."""
import re, html, sys, os, json, collections
p=sys.argv[1]; out=sys.argv[2]
sz=os.path.getsize(p); CH=64*1024*1024; OV=8*1024*1024
groups={}   # name -> {"caption","members":[...],"kind"}
seen_pos=set()
carry=b""; pos=0
with open(p,'rb') as f:
    while True:
        chunk=f.read(CH)
        if not chunk: break
        buf=carry+chunk; txt=buf.decode('utf-8','ignore')
        base=pos-len(carry)
        for m in re.finditer(r'<group\b', txt):
            st=m.start()
            if base+st in seen_pos: continue
            end=txt.find('</group>', st)
            if end<0: break  # will be picked up with carry next time
            seen_pos.add(base+st)
            seg=txt[st:end]
            head=seg[:seg.find('>')]
            nm=re.search(r'\bname=(["\'])(.*?)\1', head); cap=re.search(r'caption=(["\'])(.*?)\1', head)
            name=html.unescape(nm.group(2)) if nm else None
            if not name: continue
            mem=[html.unescape(x) for x in re.findall(r'member=(["\'])(.*?)\1', seg) for x in [x[1]]]
            lev=re.findall(r'level=(["\'])(.*?)\1', seg)
            g=groups.setdefault(name, {"caption": html.unescape(cap.group(2)) if cap else None, "members":[], "levels":set(), "n_filters":0})
            g["members"].extend(mem); g["levels"].update(l[1] for l in lev); g["n_filters"]+=seg.count('<groupfilter')
        carry=buf[-OV:]; pos+=len(chunk)
        print(f"  {pos/1e6:.0f}/{sz/1e6:.0f} MB groups={len(groups)}", file=sys.stderr, flush=True)
for g in groups.values():
    g["levels"]=sorted(g["levels"]); g["n_members"]=len(g["members"]); g["members"]=g["members"][:20000]
json.dump(groups, open(out,"w"), indent=0)
for k,g in sorted(groups.items(), key=lambda kv:-kv[1]["n_members"]):
    print(f'{g["n_members"]:>8}  {k}  cap={g["caption"]}  levels={g["levels"]}  filters={g["n_filters"]}  e.g. {g["members"][:5]}')
