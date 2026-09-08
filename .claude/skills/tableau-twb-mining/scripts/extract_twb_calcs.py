#!/usr/bin/env python3
"""Stream-extract calculated fields, parameters, worksheets from Tableau .twb files.
Big .twb files (770 MB Heimdall Demo.twb) embed data; we scan in 64 MB chunks with overlap."""
import re, html, os, sys, json
paths = sys.argv[1:]
def scan(p):
    sz=os.path.getsize(p); calcs={}; sheets=[]; params={}; groups=[]; datasources=[]
    CH=64*1024*1024; OV=2*1024*1024; carry=b""
    col_re=re.compile(r'<column\b([^>]*)>(.*?)</column>', re.S)
    sc_re=re.compile(r'<column\b([^>]*)/>')
    with open(p,'rb') as f:
        pos=0
        while True:
            chunk=f.read(CH)
            if not chunk: break
            buf=carry+chunk
            txt=buf.decode('utf-8','ignore')
            # linear split on '<column' — the lazy (.*?)</column> regex was O(n*m) on 64 MB chunks
            # because the embedded data has thousands of self-closing <column .../> tags.
            for seg in txt.split('<column')[1:]:
                gt = seg.find('>')
                if gt < 0: continue
                attrs = seg[:gt]
                selfclose = attrs.endswith('/')
                body = '' if selfclose else seg[gt+1:seg.find('</column>')] if seg.find('</column>')>=0 else ''
                if len(body) > 200000: body = ''
                cm = re.search(r'<calculation\b[^>]*formula=(["\'])(.*?)\1', body, re.S)
                cap = re.search(r'caption=(["\'])(.*?)\1', attrs); nm=re.search(r'\bname=(["\'])(.*?)\1', attrs)
                dt = re.search(r'datatype=(["\'])(.*?)\1', attrs); role=re.search(r'\brole=(["\'])(.*?)\1', attrs)
                key = html.unescape(nm.group(2)) if nm else None
                if cm and key:
                    calcs[key]={"caption": html.unescape(cap.group(2)) if cap else None,
                                "datatype": dt.group(2) if dt else None, "role": role.group(2) if role else None,
                                "formula": html.unescape(cm.group(2))}
                elif 'param-domain-type' in attrs and key:
                    val=re.search(r'value=(["\'])(.*?)\1', attrs)
                    params[key]={"caption": html.unescape(cap.group(2)) if cap else None, "value": html.unescape(val.group(2)) if val else None, "attrs": attrs[:300]}
            for m in re.finditer(r'<worksheet\b[^>]*name=(["\'])(.*?)\1', txt): sheets.append(html.unescape(m.group(2)))
            for m in re.finditer(r'<datasource\b[^>]*caption=(["\'])(.*?)\1', txt): datasources.append(html.unescape(m.group(2)))
            for m in re.finditer(r'<group\b[^>]*caption=(["\'])(.*?)\1', txt): groups.append(html.unescape(m.group(2)))
            carry=buf[-OV:]
            pos+=len(chunk); print(f"  {p}: {pos/1e6:.0f}/{sz/1e6:.0f} MB calcs={len(calcs)}", file=sys.stderr, flush=True)
    return {"size":sz,"calcs":calcs,"params":params,"sheets":sorted(set(sheets)),"datasources":sorted(set(datasources)),"groups":sorted(set(groups))}
out={}
for p in paths:
    if not os.path.exists(p): print("MISSING",p, file=sys.stderr); continue
    out[os.path.basename(p)]=scan(p)
    print(p, "calcs=",len(out[os.path.basename(p)]["calcs"]), "sheets=",len(out[os.path.basename(p)]["sheets"]), file=sys.stderr)
json.dump(out, open("00_client_demonstrations/chart_recreation/defs/twb_calcs_raw.json","w"), indent=1)
print("wrote defs/twb_calcs_raw.json")
