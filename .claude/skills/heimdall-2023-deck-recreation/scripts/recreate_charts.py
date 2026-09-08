#!/usr/bin/env python3
"""Recreate every chart of the Nov-2023 Heimdall demo deck (+ PersonasCHD.pdf) through the live
Heimdall 3.0 Matrix, with a qualitative check per chart.

Reads ONLY published memmaps/JSON (Matrix Rule #1: h is a column lookup, never recomputed):
  * audience columns  audience:saved:<slug>  (minted by scripts/mint_audience_namespace.py) — or, when
    a column is not minted yet, a READ-ONLY compose of the seed columns (matrix.audience_columns +
    matrix.combine, nothing persisted) and the chart says so.
  * rows_volume.i64 for bubble size (-1 = never measured → drawn hollow, never size 0)
  * artifacts/geo_corr/<cycle>/fps_z.f32 for the Utah axis
POI charts go through POST /api/explore (sources=poi) because the POI universe is not a Matrix row set.

Outputs (out/):  <id>.png (recreated | original side-by-side), <id>.json (data + checks), report.html

usage: recreate_charts.py [--only id,id] [--skip-poi] [--no-plot]
"""
import argparse, json, os, re, sys, time, math, random, urllib.request
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
PHASE1 = HERE.parents[1] / "06_scheme_L_2026" / "phase1"
sys.path.insert(0, str(PHASE1))
sys.path.insert(0, str(HERE))
from chart_specs import CHARTS, PS, HOP, INC, AVG                       # noqa: E402
from heimdall_core import matrix as mx                                  # noqa: E402

OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
CACHE = HERE / "cache"; CACHE.mkdir(exist_ok=True)
BASE = os.environ.get("HEIMDALL_DEMO_URL", "http://127.0.0.1:8000")
GROUPS = json.load(open(HERE / "defs" / "nov2023_groups.json"))
CATALOG = {e["name"]: e for e in json.load(open(HERE / "defs" / "audience_catalog.json"))}
AGREEMENT = {}

def slug(name): return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

def clean_member(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"': s = s[1:-1]
    return s.replace('\\"', '"').replace('\\#', '#').strip()

def group_terms(gname):
    g = GROUPS.get(gname)
    if not g: raise KeyError(gname)
    out = []
    for x in g["members"]:
        t = clean_member(x)
        if t and not t.startswith("[") and t != "[none:keyword:nk]": out.append(t)
    return list(dict.fromkeys(out))

# ── Engine: the state-fingerprint plane (2023's own data model) + the Matrix as the agreement check ──
#
# WHY THE FINGERPRINT PLANE IS PRIMARY (measured 2026-09-05 20:05): every 2023 entity row that
# matters for these charts — pinterest.com, tiktok.com, facebook.com, twitter.com … — lives in the
# Matrix's ADDENDUM rows (index ≥ n_base = 2,458,762; 729,724 rows added since the 08-28 cycle).
# Newly minted pole columns (the 2023 axes) are computed over the BASE row space only (#14374, the
# union-wide mint, is open), and the addendum extension can only fill a pole whose members are TOKEN
# columns — none of the 2023 anchors are. So for exactly the rows these charts plot, Matrix h is NaN
# (social media: 3/40 scored; tech providers 9/23; news 31/205).
#
# The 2023 charts were Pearson correlations of per-state search-volume z-vectors against anchor
# keywords. artifacts/geo_corr/<cycle>/fps_z.f32 IS that object for today's 944,329 grounded
# keywords (51 states + US), rebuilt daily — the same anchors, the same rows, the same statistic.
# Scoring there is not a workaround; it is the 2023 method on the current corpus. Matrix h is
# reported beside it wherever finite, as the new-method agreement number.
class Engine:
    def __init__(self):
        t0 = time.time(); self.m = mx.load()
        if self.m is None: raise SystemExit("no published Matrix cycle")
        m = self.m
        self.vol = np.asarray(m.row_volume) if m.row_volume is not None else None
        self.n = len(m.rows)
        print(f"[matrix] cycle {m.cycle} rows={self.n:,} base={m.n_base:,} pole_cols={len(m.pole_cols or [])} "
              f"volume={'yes' if self.vol is not None else 'NO'} in {time.time()-t0:.1f}s", flush=True)
        man = json.load(open(PHASE1 / "artifacts" / "geo_corr" / "manifest.json"))
        d = PHASE1 / "artifacts" / "geo_corr" / man["cycle"]; self.fp_cycle = man["cycle"]
        self.geo_order = json.load(open(d / "geo_order.json")); self.ui = self.geo_order.index("Utah")
        self.fp_kws = json.load(open(d / "fp_keywords.json")); self.fp_idx = {k.lower(): i for i, k in enumerate(self.fp_kws)}
        fz = np.memmap(d / "fps_z.f32", dtype=np.float32, mode="r", shape=(len(self.fp_kws), len(self.geo_order)))
        self.fz = fz; ns = len(self.geo_order) - 1                       # drop 'United States' (constant 0)
        Z = np.array(fz[:, :ns], dtype=np.float32); Z -= Z.mean(1, keepdims=True)
        nrm = np.linalg.norm(Z, axis=1, keepdims=True); nrm[nrm == 0] = np.nan
        self.Zn = Z / nrm                                                # row-normalised → dot = Pearson r
        self.fp_vol = self._fp_volume()
        print(f"[fp] state fingerprint cycle {self.fp_cycle}: {len(self.fp_kws):,} keywords × {ns} states in {time.time()-t0:.1f}s", flush=True)
        self._fp_score = {}; self._col = {}; self.col_source = {}; self.agreement = {}
    def _fp_volume(self):
        """Google volume per fingerprint keyword via the Matrix's row-aligned volume memmap (row_of works
        for addendum rows too). -1/missing → NaN."""
        v = np.full(len(self.fp_kws), np.nan, np.float32)
        if self.vol is None: return v
        for i, k in enumerate(self.fp_kws):
            r = self.m.row_of(k)
            if r is not None and r < len(self.vol) and self.vol[r] >= 0: v[i] = self.vol[r]
        return v
    # ---- scoring -------------------------------------------------------------------------
    def fp_score(self, name):
        """2023 formula on the fingerprint plane: Σ w_a · r(keyword, anchor_a) / Σ|w_a|."""
        if name in self._fp_score: return self._fp_score[name]
        e = CATALOG[name]; ws, vecs, used, cold = [], [], [], []
        for s in e["seeds"]:
            w, bare = mx.parse_term(s); i = self.fp_idx.get(bare.lower())
            if i is None or not np.isfinite(self.Zn[i]).all(): cold.append(bare); continue
            ws.append(w); vecs.append(self.Zn[i]); used.append(bare)
        if len(vecs) < 2:
            print(f"[fp] {name}: only {len(vecs)}/{len(e['seeds'])} anchors in the fingerprint corpus — UNAVAILABLE (cold: {cold[:6]})", flush=True)
            self._fp_score[name] = None; self.col_source[name] = f"fp: unavailable ({len(vecs)}/{len(e['seeds'])} anchors)"; return None
        A = np.stack(vecs); w = np.asarray(ws, np.float32)
        R = self.Zn @ A.T                                                # (944k, n_anchors) Pearson r
        sc = (R @ w) / np.abs(w).sum()
        self._fp_score[name] = sc.astype(np.float32)
        self.col_source[name] = f"fp: {len(used)}/{len(e['seeds'])} anchors on {self.fp_cycle}" + (f" (cold: {cold[:4]})" if cold else "")
        # agreement with Matrix h where both exist
        h = self.matrix_col(name)
        if h is not None:
            mi = np.array([self.m.row_of(k) if self.m.row_of(k) is not None else -1 for k in self.fp_kws[:200000]])
            ok = mi >= 0; hv = np.full(len(mi), np.nan, np.float32); hv[ok] = h[mi[ok]]
            both = np.isfinite(hv) & np.isfinite(sc[:200000])
            r = float(np.corrcoef(hv[both], sc[:200000][both])[0, 1]) if both.sum() > 100 else float("nan")
            self.agreement[name] = {"n": int(both.sum()), "r": round(r, 3)}; AGREEMENT[name] = self.agreement[name]
            print(f"[fp] {name}: {self.col_source[name]} · Matrix-h agreement r={r:+.3f} on {both.sum():,} rows", flush=True)
        else:
            print(f"[fp] {name}: {self.col_source[name]} · Matrix column absent", flush=True)
        return self._fp_score[name]
    def matrix_col(self, name):
        if name in self._col: return self._col[name]
        c = self.m.column("audience:saved:" + slug(name))
        if c is not None:
            c = np.asarray(c, dtype=np.float32)
            if c.shape[0] < self.n: c = np.concatenate([c, np.full(self.n - c.shape[0], np.nan, np.float32)])
        self._col[name] = c; return c
    # ---- row lookup ----------------------------------------------------------------------
    def fp_rows_of(self, terms):
        idx, miss = [], []
        for t in terms:
            i = self.fp_idx.get(t.lower())
            if i is None: miss.append(t)
            else: idx.append((i, t))
        return idx, miss
    def regex_rows(self, pattern, min_volume=0, top=None, contains=None):
        rx = re.compile(pattern, re.I)
        hits = [i for i, r in enumerate(self.fp_kws) if rx.search(r) and (not contains or contains in r.lower())]
        if min_volume or top:
            hits = [i for i in hits if np.isfinite(self.fp_vol[i]) and self.fp_vol[i] >= max(min_volume, 1)]
            hits.sort(key=lambda i: -float(self.fp_vol[i]))
        if top: hits = hits[:top]
        return hits

# ── derived axes ────────────────────────────────────────────────────────────────────────
def seg_contrast(seg, avg): return (seg * .22 - avg * .75) * 2
def ubiquity(v, avg):
    a = np.abs(avg); a = np.where(np.isfinite(a) & (a > 0.01), a, np.nan)
    u = np.sqrt(np.where(v > 0, v, np.nan) / a)
    p99 = np.nanpercentile(u, 99) if np.isfinite(u).any() else 1.0
    return u / p99

# ── qualitative checks ──────────────────────────────────────────────────────────────────
def landmark_checks(spec, terms, x, y):
    out = []; med_x = float(np.nanmedian(x)) if np.isfinite(x).any() else 0; med_y = float(np.nanmedian(y)) if np.isfinite(y).any() else 0
    tl = {t.lower(): k for k, t in enumerate(terms)}
    for term, exp in spec.get("landmarks", []):
        k = tl.get(term.lower())
        if k is None or not (np.isfinite(x[k]) and np.isfinite(y[k])):
            out.append({"term": term, "expected": exp, "result": "absent"}); continue
        ok = True
        if "x+" in exp: ok &= x[k] > med_x
        if "x-" in exp: ok &= x[k] < med_x
        if "y+" in exp: ok &= y[k] > med_y
        if "y-" in exp: ok &= y[k] < med_y
        out.append({"term": term, "expected": exp, "x": round(float(x[k]), 4), "y": round(float(y[k]), 4), "result": "pass" if ok else "FAIL"})
    return out

def verdict(res):
    n = res["n_rows"]; f = res["n_found"]; s = res["n_scored"]; lm = res["landmarks"]
    passed = sum(1 for l in lm if l["result"] == "pass"); tested = sum(1 for l in lm if l["result"] != "absent")
    parts = []
    parts.append(f"{f}/{n} rows in Matrix ({100*f/max(n,1):.0f}%)"); parts.append(f"{s} scored on both axes")
    if tested: parts.append(f"landmarks {passed}/{tested} in the expected half")
    if res.get("corr_xy") is not None: parts.append(f"r(x,y)={res['corr_xy']:+.2f}")
    ms = res.get("min_scored", 10)
    grade = "GOOD" if (f / max(n, 1) >= .5 and s >= max(20, ms) and (tested == 0 or passed / tested >= .6)) else ("PARTIAL" if s >= ms else "NOT RECREATED")
    return grade, "; ".join(parts)

# ── plotting ────────────────────────────────────────────────────────────────────────────
def plot(spec, terms, x, y, v, color, res, xlabel, ylabel, extra_panels=None):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image
    fin = np.isfinite(x) & np.isfinite(y)
    orig = HERE / "src_slides" / f"s-{int(spec['slide']):02d}.png" if isinstance(spec["slide"], int) else HERE / "src_personas" / "p-1.png"
    npan = 1 + (len(extra_panels) if extra_panels else 0)
    fig = plt.figure(figsize=(9.5 * npan + 9, 8))
    gs = fig.add_gridspec(1, npan + 1, width_ratios=[1.0] * npan + [1.05])
    axes = [fig.add_subplot(gs[0, k]) for k in range(npan + 1)]
    def one(ax, xx, yy, xl, title):
        f2 = np.isfinite(xx) & np.isfinite(yy)
        vv = np.where(v > 0, v, np.nan)
        size = np.where(np.isfinite(vv), 12 + 260 * np.sqrt(vv / np.nanmax(vv)) if np.isfinite(vv).any() else 20, 14)
        cc = color if color is not None else xx
        sc = ax.scatter(xx[f2], yy[f2], s=size[f2], c=cc[f2], cmap="RdYlGn", alpha=.55, linewidths=.3, edgecolors="k")
        hollow = f2 & ~np.isfinite(vv)
        if hollow.any(): ax.scatter(xx[hollow], yy[hollow], s=14, facecolors="none", edgecolors="grey", linewidths=.5)
        # labels: landmarks + top-12 by volume
        lab = {t.lower() for t, _ in spec.get("landmarks", [])}
        order = np.argsort(-np.nan_to_num(vv, nan=-1))
        nlab = len(terms) if len(terms) <= 90 else (40 if len(terms) <= 600 else 24)
        # extremes are what the eye reads on the original — label the corners too
        fx = np.where(f2)[0]
        corners = list(fx[np.argsort(xx[fx])][:4]) + list(fx[np.argsort(xx[fx])][-4:]) + list(fx[np.argsort(yy[fx])][:4]) + list(fx[np.argsort(yy[fx])][-4:]) if len(fx) else []
        picks = [k for k in order[:nlab] if f2[k]] + [k for k, t in enumerate(terms) if t.lower() in lab and f2[k]] + [int(k) for k in corners]
        for k in dict.fromkeys(picks):
            ax.annotate(terms[k][:26], (xx[k], yy[k]), fontsize=6.5, alpha=.9, xytext=(3, 2), textcoords="offset points")
        ax.axhline(np.nanmedian(yy), color="grey", lw=.5); ax.axvline(np.nanmedian(xx), color="grey", lw=.5)
        if spec.get("rows", {}).get("poi") and spec.get("x") == "UBQ": ax.invert_xaxis()   # 2023 drew Ubiquity 5000% → 0% left-to-right
        ax.set_xlabel(xl); ax.set_ylabel(ylabel); ax.set_title(title, fontsize=10)
        return sc
    one(axes[0], x, y, xlabel, f"RECREATED · {spec['title']} · {res['grade']}\n{res['summary']}"[:170])
    if extra_panels:
        for ax, (xl, xx) in zip(axes[1:-1], extra_panels): one(ax, xx, y, xl, f"RECREATED · X = {xl}")
    if orig.exists():
        im = Image.open(orig); axes[-1].imshow(im); axes[-1].axis("off"); axes[-1].set_title(f"ORIGINAL · slide {spec['slide']}", fontsize=10)
    fig.tight_layout(); p = OUT / f"{spec['id']}.png"; fig.savefig(p, dpi=110); plt.close(fig); return p

# ── explore (POI) ───────────────────────────────────────────────────────────────────────
def explore_poi(spec, eng, sample=40000):
    auds = [{"name": HOP, "terms": CATALOG[HOP]["seeds"], "slot": 0},
            {"name": AVG, "terms": CATALOG[AVG]["seeds"], "slot": 1},
            {"name": PS, "terms": CATALOG[PS]["seeds"], "slot": 2}]
    body = {"audiences": auds, "sample": sample, "sources": ["poi"], "regions": ["corpus_only", "both"], "seed": 7, "poi_population": "fingerprint"}
    for attempt in range(12):
        try:
            req = urllib.request.Request(BASE + "/api/explore", data=json.dumps(body).encode(), headers={"content-type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=1500))
        except Exception as e:
            print(f"[poi] explore attempt {attempt+1}: {type(e).__name__}: {e}", flush=True); time.sleep(30); continue
        if r.get("pending") or r.get("partial"):
            print(f"[poi] explore partial/pending (cold={r.get('cold_terms')}) — retry in 45s", flush=True); time.sleep(45); continue
        return r
    return None

# ── main per-chart driver ───────────────────────────────────────────────────────────────
def run_chart(spec, eng, do_plot=True):
    t0 = time.time(); rows = spec.get("rows", {})
    res = {"id": spec["id"], "slide": spec["slide"], "title": spec["title"], "note": spec.get("note", ""), "axes": {}, "min_scored": spec.get("min_scored", 10)}
    if spec.get("chd"): return run_chd(spec, eng, res, do_plot)
    if rows.get("poi"): return run_poi(spec, eng, res, do_plot)
    # 1. row source
    terms = []
    if "group" in rows: terms = group_terms(rows["group"])
    if "groups" in rows:
        for g in rows["groups"]: terms += group_terms(g)
    if rows.get("contains"): terms = [t for t in terms if rows["contains"] in t.lower()]
    if rows.get("regex_filter"): _rf = re.compile(rows["regex_filter"], re.I); terms = [t for t in terms if _rf.search(t)]
    if rows.get("gads"): return run_gads(spec, eng, res, do_plot)
    if "terms" in rows: terms = list(rows["terms"])
    idx_terms = []
    if terms:
        if rows.get("sample") and len(terms) > rows["sample"]:
            random.seed(11); terms = random.sample(terms, rows["sample"])
        idx_terms, miss = eng.fp_rows_of(terms)
        res["n_rows"] = len(terms); res["missing_examples"] = miss[:12]
    elif "regex" in rows:
        hits = eng.regex_rows(rows["regex"], rows.get("min_volume", 0), rows.get("top"), rows.get("contains"))
        idx_terms = [(i, eng.fp_kws[i]) for i in hits]; res["n_rows"] = len(hits); res["missing_examples"] = []
    elif "corpus_sample" in rows:
        random.seed(5); n = len(eng.fp_kws)
        pool = random.sample(range(n), min(rows["corpus_sample"] * 2, n))
        pool = [i for i in pool if np.isfinite(eng.fp_vol[i]) and eng.fp_vol[i] > 0][:rows["corpus_sample"]]
        idx_terms = [(i, eng.fp_kws[i]) for i in pool]; res["n_rows"] = len(pool); res["missing_examples"] = []
    if rows.get("regex_extra"):
        extra = eng.regex_rows(rows["regex_extra"], rows.get("min_volume_extra", 0), 400)
        seen = {i for i, _ in idx_terms}; idx_terms += [(i, eng.fp_kws[i]) for i in extra if i not in seen]; res["n_rows"] += len(extra)
    # de-duplicate fingerprint rows (a group can list 'LinkedIn' and 'linkedin')
    _seen = set(); idx_terms = [(i, t) for i, t in idx_terms if not (i in _seen or _seen.add(i))]
    if rows.get("top") and "group" in rows:
        idx_terms.sort(key=lambda it: -float(np.nan_to_num(eng.fp_vol[it[0]], nan=-1))); idx_terms = idx_terms[:rows["top"]]
    res["n_found"] = len(idx_terms)
    if not idx_terms:
        res.update(n_scored=0, landmarks=[], grade="NOT RECREATED", summary="no rows found in the fingerprint corpus"); return res
    ii = np.array([i for i, _ in idx_terms]); tt = [t for _, t in idx_terms]
    v = eng.fp_vol[ii].astype(float)
    # 2. axes — 2023 formula on the fingerprint plane (see Engine docstring)
    def axis(name):
        if name == "SC":
            seg = eng.fp_score(spec.get("seg", PS)); avg = eng.fp_score(AVG)
            return (seg_contrast(seg[ii], avg[ii]) if seg is not None and avg is not None else np.full(len(ii), np.nan)), "Segment Contrast (PS)"
        if name == "UBQ":
            avg = eng.fp_score(AVG); return (ubiquity(v, avg[ii]) if avg is not None else np.full(len(ii), np.nan)), "Ubiquity (sqrt vol/avg-person, /p99)"
        if name == "UT":
            return np.array(eng.fz[ii, eng.ui], float), "Utah z-score (state fingerprint)"
        c = eng.fp_score(name); return (c[ii] if c is not None else np.full(len(ii), np.nan)), name
    if spec.get("matrix"):   # scatter-matrix chart
        return run_matrix_chart(spec, eng, res, ii, tt, v, axis, do_plot)
    if spec.get("panels"):   # small multiples
        return run_panels_chart(spec, eng, res, ii, tt, v, axis, do_plot)
    x, xl = axis(spec["x"]); y, yl = axis(spec["y"])
    color = None
    if spec.get("color"): color, _ = axis(spec["color"])
    res["axes"] = {"x": xl, "y": yl, "x_source": eng.col_source.get(spec["x"]), "y_source": eng.col_source.get(spec["y"])}
    fin = np.isfinite(x) & np.isfinite(y); res["n_scored"] = int(fin.sum()); res["n_with_volume"] = int(np.isfinite(v).sum())
    res["corr_xy"] = round(float(np.corrcoef(x[fin], y[fin])[0, 1]), 3) if fin.sum() > 5 else None
    res["landmarks"] = landmark_checks(spec, tt, x, y)
    o = np.argsort(np.nan_to_num(x, nan=0)); res["x_low"] = [tt[k] for k in o[:8] if fin[k]]; res["x_high"] = [tt[k] for k in o[::-1][:8] if fin[k]]
    o = np.argsort(np.nan_to_num(y, nan=0)); res["y_low"] = [tt[k] for k in o[:8] if fin[k]]; res["y_high"] = [tt[k] for k in o[::-1][:8] if fin[k]]
    ov = np.argsort(-np.nan_to_num(v, nan=-1)); res["top_volume"] = [(tt[k], int(v[k])) for k in ov[:8] if np.isfinite(v[k])]
    res["grade"], res["summary"] = verdict(res)
    extra = []
    if spec.get("x2"):
        x2, x2l = axis(spec["x2"]); extra.append((x2l, x2)); res["axes"]["x2"] = x2l
    if do_plot: res["png"] = str(plot(spec, tt, x, y, v, color, res, xl, yl, extra).name)
    res["seconds"] = round(time.time() - t0, 1)
    json.dump({**res, "points": [{"w": tt[k], "x": None if not np.isfinite(x[k]) else round(float(x[k]), 4), "y": None if not np.isfinite(y[k]) else round(float(y[k]), 4),
                                  "v": None if not np.isfinite(v[k]) else int(v[k])} for k in range(len(tt))][:60000]},
              open(OUT / f"{spec['id']}.json", "w"))
    return res

def run_panels_chart(spec, eng, res, ii, tt, v, axis, do_plot):
    y, yl = axis(spec["y"]); color, _ = axis(spec["color"]); panels = []
    for pn in spec["panels"]:
        x, xl = axis(pn); fin = np.isfinite(x) & np.isfinite(y)
        r = round(float(np.corrcoef(x[fin], y[fin])[0, 1]), 3) if fin.sum() > 5 else None
        panels.append({"x": xl, "n_scored": int(fin.sum()), "corr_xy": r, "source": eng.col_source.get(pn)})
    res.update(n_scored=max(p["n_scored"] for p in panels), panels=panels, landmarks=[], corr_xy=panels[0]["corr_xy"])
    res["grade"], res["summary"] = verdict(res); res["summary"] += " · slopes: " + ", ".join(f"{p['x'].split(' (')[0]}={p['corr_xy']}" for p in panels)
    if do_plot:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt; from PIL import Image
        fig, axes = plt.subplots(1, len(panels) + 1, figsize=(4.2 * (len(panels) + 1), 5))
        for ax, pn in zip(axes[:-1], spec["panels"]):
            x, xl = axis(pn); fin = np.isfinite(x) & np.isfinite(y)
            ax.scatter(x[fin], y[fin], s=4 + 40 * np.sqrt(np.nan_to_num(v[fin], nan=0) / max(np.nanmax(v), 1)), c=color[fin], cmap="RdYlGn_r", alpha=.4, linewidths=0)
            if fin.sum() > 5:
                b = np.polyfit(x[fin], y[fin], 1); xs = np.linspace(np.nanmin(x[fin]), np.nanmax(x[fin]), 2); ax.plot(xs, b[0] * xs + b[1], "k-", lw=1)
            ax.set_title(pn.replace(" (2023)", ""), fontsize=8); ax.set_xlabel("segment h"); ax.set_ylabel("Hopscotch h")
        orig = HERE / "src_slides" / f"s-{spec['slide']:02d}.png"; axes[-1].imshow(Image.open(orig)); axes[-1].axis("off"); axes[-1].set_title("ORIGINAL", fontsize=9)
        fig.suptitle(f"RECREATED · {spec['title']} · {res['grade']} · {res['summary']}"[:200], fontsize=9); fig.tight_layout()
        p = OUT / f"{spec['id']}.png"; fig.savefig(p, dpi=110); plt.close(fig); res["png"] = p.name
    json.dump(res, open(OUT / f"{spec['id']}.json", "w"), default=str); return res

def run_matrix_chart(spec, eng, res, ii, tt, v, axis, do_plot):
    cols = [axis(n) for n in spec["matrix"]]; k = len(cols)
    res.update(n_scored=int(np.isfinite(np.stack([c for c, _ in cols])).all(0).sum()), landmarks=landmark_checks(spec, tt, cols[1][0], cols[2][0]),
               corr_xy=round(float(np.corrcoef(*[c[np.isfinite(cols[1][0]) & np.isfinite(cols[2][0])] for c, _ in cols[1:3]])[0, 1]), 3))
    res["grade"], res["summary"] = verdict(res)
    if do_plot:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt; from PIL import Image
        fig = plt.figure(figsize=(3 * k + 6, 3 * k)); gs = fig.add_gridspec(k, k + 2)
        for r in range(k):
            for c in range(k):
                ax = fig.add_subplot(gs[r, c]); xx, xl = cols[c]; yy, yl = cols[r]; fin = np.isfinite(xx) & np.isfinite(yy)
                ax.scatter(xx[fin], yy[fin], s=3 + 30 * np.sqrt(np.nan_to_num(v[fin], nan=0) / max(np.nanmax(v), 1)), c=cols[3][0][fin], cmap="RdYlGn", alpha=.5, linewidths=0)
                if r == k - 1: ax.set_xlabel(xl[:22], fontsize=7)
                if c == 0: ax.set_ylabel(yl[:22], fontsize=7)
                ax.tick_params(labelsize=6)
        ax = fig.add_subplot(gs[:, k:]); ax.imshow(Image.open(HERE / "src_slides" / f"s-{spec['slide']:02d}.png")); ax.axis("off"); ax.set_title("ORIGINAL", fontsize=9)
        fig.suptitle(f"RECREATED · {spec['title']} · {res['grade']} · {res['summary']}"[:200], fontsize=9); fig.tight_layout()
        p = OUT / f"{spec['id']}.png"; fig.savefig(p, dpi=100); plt.close(fig); res["png"] = p.name
    json.dump(res, open(OUT / f"{spec['id']}.json", "w"), default=str); return res

def run_gads(spec, eng, res, do_plot):
    """Rows = Google audiences, placed the way the 2023 workbook placed them: each segment's dot is the
    (weight-)mean of its MEMBER keywords' scores — avg(zn([anchor])) over the segment's rows — with the
    members read from the engine's published formulas (staging/audience_formulas.json, lock-free) and the
    scores from the fingerprint plane. Size = Σ member Google volume. Labels from col_labels.json.

    (A first cut correlated the Matrix's gads COLUMNS with the PS/HOP columns; measured r(x,y)=0.99 even
    after regressing Average Person out — the composed Matrix audience columns share a dominant common
    factor across Google columns, so that read carried no information. Kept here as the reason.)"""
    m = eng.m; fam = spec["rows"]["gads"]
    F = json.load(open(PHASE1 / "staging" / "audience_formulas.json"))["formulas"]
    labels = {}
    try: labels = json.load(open(m.dir / "col_labels.json")).get("labels", {})
    except Exception: pass
    ps = eng.fp_score(PS); hop = eng.fp_score(HOP)
    tt, xs, ys, vs, ns = [], [], [], [], []
    for key, members in F.items():
        if not key.startswith("gads:" + fam + ":"): continue
        idx, w = [], []
        for mem in members:
            i = eng.fp_idx.get(str(mem.get("set_key", "")).lower())
            if i is None or mem.get("weight", 0) <= 0: continue
            idx.append(i); w.append(float(mem["weight"]))
        if len(idx) < 3: continue
        idx = np.array(idx); w = np.array(w, np.float32)
        fx = np.isfinite(ps[idx]) & np.isfinite(hop[idx])
        if fx.sum() < 3: continue
        ww = w[fx] / w[fx].sum()
        tt.append(labels.get("audience:" + key, {}).get("n") or key); xs.append(float(ww @ ps[idx][fx])); ys.append(float(ww @ hop[idx][fx]))
        vol = eng.fp_vol[idx][fx]; vs.append(float(np.nansum(vol)) if np.isfinite(vol).any() else np.nan); ns.append(int(fx.sum()))
    x, y, v = np.array(xs), np.array(ys), np.array(vs)
    res.update(n_rows=sum(1 for k in F if k.startswith("gads:" + fam + ":")), n_found=len(tt), n_scored=len(tt), members_median=int(np.median(ns)) if ns else 0)
    res["axes"] = {"x": "mean PS of member keywords (fp plane)", "y": "mean Hopscotch of member keywords (fp plane)", "size": "Σ member Google volume"}
    fin = np.isfinite(x) & np.isfinite(y); res["corr_xy"] = round(float(np.corrcoef(x[fin], y[fin])[0, 1]), 3) if fin.sum() > 5 else None
    res["landmarks"] = landmark_checks(spec, tt, x, y)
    o = np.argsort(x); res["x_low"] = [tt[k] for k in o[:8]]; res["x_high"] = [tt[k] for k in o[::-1][:8]]
    o = np.argsort(y); res["y_low"] = [tt[k] for k in o[:8]]; res["y_high"] = [tt[k] for k in o[::-1][:8]]
    res["grade"], res["summary"] = verdict(res)
    if do_plot: res["png"] = plot(spec, tt, x, y, v, x, res, "Political Spectrum (member mean)", "Hopscotch (member mean)").name
    json.dump({**res, "points": [{"w": tt[k], "x": round(float(x[k]), 4), "y": round(float(y[k]), 4), "v": None if not np.isfinite(v[k]) else int(v[k])} for k in range(len(tt))]}, open(OUT / f"{spec['id']}.json", "w")); return res

def poi_plane(eng, min_locations=3):
    """POI × audience on the 2023 statistic: Pearson between a POI's per-state physical-location SHARE
    (z-scored across states, the volume-to-reach normalisation Cerebro applied to keywords) and the
    audience anchors' state z-vectors. Source: artifacts/poi/<version>/poi-fingerprints.npz (OSM,
    1,325,263 POI terms × 53 states, google_geo_ids aligned to the keyword fingerprint's geo_axis)."""
    if getattr(eng, "_poi", None) is not None: return eng._poi
    import scipy.sparse as sp
    vdir = sorted((PHASE1 / "artifacts" / "poi").glob("osm-*"))[-1]
    z = np.load(vdir / "poi-fingerprints.npz", allow_pickle=True)
    kws = z["keywords"]; shape = tuple(z["poi_state_shape"])
    M = sp.csr_matrix((z["poi_state_data"], z["poi_state_indices"], z["poi_state_indptr"]), shape=shape)
    gids = list(z["poi_state_google_geo_ids"]); mask = z["poi_state_alignment_mask"]
    axis = json.load(open(PHASE1 / "artifacts" / "geo_corr" / eng.fp_cycle / "geo_axis.json"))   # keyword fingerprint state order (google ids)
    col_of = {g: j for j, g in enumerate(gids) if mask[j]}
    order = [col_of.get(g) for g in axis[:51]]                        # POI column for each fingerprint state column
    keep = [k for k, j in enumerate(order) if j is not None]; pc = [order[k] for k in keep]
    tot = np.asarray(M.sum(1)).ravel(); sel = np.where(tot >= min_locations)[0]
    D = np.asarray(M[sel][:, pc].todense(), dtype=np.float32)          # (n_poi, n_states) counts
    state_tot = np.asarray(M.sum(0)).ravel()[pc].astype(np.float32); state_tot[state_tot == 0] = np.nan
    S = D / state_tot                                                 # share of each state's POIs (volume-to-reach)
    S = S / np.nansum(S, 1, keepdims=True)
    Zs = S - np.nanmean(S, 1, keepdims=True); nrm = np.linalg.norm(np.nan_to_num(Zs), axis=1, keepdims=True); nrm[nrm == 0] = np.nan
    Zn = np.nan_to_num(Zs) / nrm
    eng._poi = {"kws": [str(kws[i]) for i in sel], "Zn": Zn, "keep": keep, "tot": tot[sel], "utah_share": (D[:, keep.index(eng.geo_order.index("Utah"))] / tot[sel]) if "Utah" in eng.geo_order and eng.geo_order.index("Utah") in keep else None,
                "version": vdir.name, "n_states": len(keep)}
    print(f"[poi] {vdir.name}: {len(sel):,} POI terms with ≥{min_locations} locations × {len(keep)} aligned states", flush=True)
    return eng._poi

def poi_score(eng, name):
    P = poi_plane(eng); key = "poi:" + name
    if key in eng._fp_score: return eng._fp_score[key]
    e = CATALOG[name]; ws, vecs = [], []
    for s_ in e["seeds"]:
        w, bare = mx.parse_term(s_); i = eng.fp_idx.get(bare.lower())
        if i is None or not np.isfinite(eng.Zn[i]).all(): continue
        ws.append(w); vecs.append(eng.Zn[i][P["keep"]])
    A = np.stack(vecs); A = A - A.mean(1, keepdims=True); A /= np.linalg.norm(A, axis=1, keepdims=True)
    w = np.asarray(ws, np.float32); sc = (P["Zn"] @ A.T) @ w / np.abs(w).sum()
    eng._fp_score[key] = sc.astype(np.float32); return eng._fp_score[key]

def run_poi(spec, eng, res, do_plot):
    P = poi_plane(eng); tt = P["kws"]; hop = poi_score(eng, HOP); avg = poi_score(eng, AVG); ps = poi_score(eng, PS)
    v = P["tot"].astype(float)                                        # bubble = number of physical locations
    res.update(n_rows=len(tt), n_found=len(tt), poi_version=P["version"])
    if spec["x"] == "UBQ":
        x = np.log10(v); xl = "Ubiquity = log10(physical locations) (2023: sqrt(volume/avg-person))"
    elif spec["x"] == "SC": x, xl = seg_contrast(hop, avg), "Segment Contrast (Hopscotch vs Average Person)"
    elif spec["x"] == "UT":
        x = P["utah_share"]; xl = "Utah share of locations (2023 _Utahish)"
    y, yl = (hop, "Hopscotch (POI state-share Pearson)") if spec["y"] == HOP else (seg_contrast(hop, avg), "Segment Contrast")
    if spec["rows"].get("utah"):
        keep = x > 0.02; x, y, v, ps, tt = x[keep], y[keep], v[keep], ps[keep], [t for t, k in zip(tt, keep) if k]
        res["n_found"] = res["n_rows"] = len(tt); res["note"] += f" Filtered to POIs with ≥2% of locations in Utah ({len(tt):,})."
    if spec["id"] == "25_poi_3_zoom":
        keep = y >= np.nanpercentile(y, 97); x, y, v, ps, tt = x[keep], y[keep], v[keep], ps[keep], [t for t, k in zip(tt, keep) if k]
        res["n_found"] = res["n_rows"] = len(tt); res["note"] += f" Zoomed to the top-3% Hopscotch POIs ({len(tt):,})."
    fin = np.isfinite(x) & np.isfinite(y); res["n_scored"] = int(fin.sum()); res["axes"] = {"x": xl, "y": yl, "plane": "POI state-share × keyword fingerprint anchors"}
    res["corr_xy"] = round(float(np.corrcoef(x[fin], y[fin])[0, 1]), 3) if fin.sum() > 5 else None
    res["landmarks"] = landmark_checks(spec, tt, x, y); res["grade"], res["summary"] = verdict(res)
    o = np.argsort(np.nan_to_num(y, nan=0)); res["y_low"] = [tt[k] for k in o[:8] if fin[k]]; res["y_high"] = [tt[k] for k in o[::-1][:8] if fin[k]]
    o = np.argsort(np.nan_to_num(x, nan=0)); res["x_low"] = [tt[k] for k in o[:8] if fin[k]]; res["x_high"] = [tt[k] for k in o[::-1][:8] if fin[k]]
    ov = np.argsort(-v); res["top_volume"] = [(tt[k], int(v[k])) for k in ov[:10]]
    if do_plot:
        # cap the drawn cloud for the renderer; keep every high-volume POI and a random 25k of the rest
        if len(tt) > 30000:
            random.seed(2); big = set(np.argsort(-v)[:5000].tolist()); rest = [k for k in range(len(tt)) if k not in big]; pick = sorted(big | set(random.sample(rest, 25000)))
            tt2 = [tt[k] for k in pick]; res["png"] = plot(spec, tt2, x[pick], y[pick], v[pick], ps[pick], res, xl, yl).name
        else:
            res["png"] = plot(spec, tt, x, y, v, ps, res, xl, yl).name
    json.dump(res, open(OUT / f"{spec['id']}.json", "w")); return res

def run_chd(spec, eng, res, do_plot):
    rg, gm = (eng.fp_score(n) for n in spec["x"])
    # Risk of Leaving = the two 2017 attributes pooled into one pole (their seeds are still onboarding —
    # 1/11 + 3/17 grounded today — so each alone is too thin; the union is scored as one formula and the
    # chart says how many anchors it stands on).
    CATALOG["CHD Risk of Leaving (pooled)"] = {"name": "CHD Risk of Leaving (pooled)", "seeds": CATALOG[spec["y"][0]]["seeds"] + CATALOG[spec["y"][1]]["seeds"]}
    risk = eng.fp_score("CHD Risk of Leaving (pooled)"); lf = da = risk
    if any(c is None for c in (rg, gm, risk)):
        res.update(n_rows=12, n_found=0, n_scored=0, landmarks=[], grade="NOT RECREATED",
                   summary="CHD axis audiences not yet composable (seeds still onboarding): " + ", ".join(f"{n}={eng.col_source.get(n)}" for n in list(spec['x']) + list(spec['y']))); return res
    personas = [e for e in CATALOG.values() if e.get("role") == "persona"]; pts = []
    for p in personas:
        idx, miss = eng.fp_rows_of([mx.parse_term(s)[1] for s in p["seeds"]])
        ii = np.array([i for i, _ in idx], int) if idx else np.array([], int)
        if len(ii) == 0: pts.append({"w": p["name"], "x": np.nan, "y": np.nan, "v": np.nan, "members": 0}); continue
        x = np.nanmean(rg[ii] - gm[ii]); y = np.nanmean((lf[ii] + da[ii]) / 2); vv = eng.fp_vol[ii]; vv = vv[np.isfinite(vv) & (vv > 0)]
        pts.append({"w": p["name"], "x": x, "y": y, "v": float(vv.sum()) if len(vv) else np.nan, "members": int(len(ii)), "member_terms": [eng.fp_kws[i] for i in ii]})
    tt = [q["w"] for q in pts]; x = np.array([q["x"] for q in pts]); y = np.array([q["y"] for q in pts]); v = np.array([q["v"] for q in pts])
    fin = np.isfinite(x) & np.isfinite(y); res.update(n_rows=len(pts), n_found=int(sum(q["members"] > 0 for q in pts)), n_scored=int(fin.sum()), personas=pts)
    res["axes"] = {"x": "corr(Rising Generation) − corr(General Membership)", "y": "Risk of Leaving (Losing Faith ∪ Disaffected LDS, pooled)", "sources": {n: eng.col_source.get(n) for n in list(spec["x"]) + ["CHD Risk of Leaving (pooled)"]}}
    res["landmarks"] = landmark_checks(spec, tt, x, y); res["corr_xy"] = None; res["grade"], res["summary"] = verdict(res)
    if do_plot: res["png"] = plot(spec, [t.replace("CHD Persona: ", "") for t in tt], x, y, v, None, res, res["axes"]["x"], res["axes"]["y"]).name
    json.dump(res, open(OUT / f"{spec['id']}.json", "w"), default=str); return res

def write_report(results):
    # the report always covers EVERY chart: merge this run's results over the last saved per-chart JSON
    saved = {}
    for spec in CHARTS:
        f = OUT / f"{spec['id']}.json"
        if f.exists():
            try:
                d = json.load(open(f)); d.pop("points", None); saved[spec["id"]] = d
            except Exception: pass
    for r in results: saved[r["id"]] = r
    results = [saved[spec["id"]] for spec in CHARTS if spec["id"] in saved]
    rows = []
    for r in results:
        lm = "".join(f"<li class={l['result']}>{l['term']} — expected {l['expected']} → {l['result']}" + (f" (x={l['x']}, y={l['y']})" if 'x' in l else "") + "</li>" for l in r.get("landmarks", []))
        rows.append(f"""<section><h2>{r['title']} <small>slide {r['slide']} · <b class={r['grade'].replace(' ','_')}>{r['grade']}</b></small></h2>
        <p>{r.get('summary','')}</p><p class=note>{r.get('note','')}</p>
        {'<img src="'+r['png']+'">' if r.get('png') else ''}
        <details><summary>details</summary><ul>{lm}</ul>
        <p>x high: {r.get('x_high')}<br>x low: {r.get('x_low')}<br>y high: {r.get('y_high')}<br>y low: {r.get('y_low')}<br>top volume: {r.get('top_volume')}<br>
        missing examples: {r.get('missing_examples')}<br>axes: {r.get('axes')}</p></details></section>""")
    agree = "".join(f"<li>{n}: {a['r']:+.3f} on {a['n']:,} base rows</li>" for n, a in AGREEMENT.items())
    html = f"""<!doctype html><meta charset=utf-8><title>Heimdall Nov 2023 deck — recreated through Heimdall 3.0</title>
    <style>body{{font-family:-apple-system,Helvetica,sans-serif;max-width:1500px;margin:20px auto;padding:0 20px}} img{{max-width:100%;border:1px solid #ddd}}
    .GOOD{{color:#1a7f37}} .PARTIAL{{color:#b26a00}} .NOT_RECREATED{{color:#b00020}} li.pass{{color:#1a7f37}} li.FAIL{{color:#b00020}} li.absent{{color:#888}} .note{{color:#555;font-size:.9em}}</style>
    <h1>Heimdall Nov 2023 demo deck + PersonasCHD — recreated through the live Matrix ({time.strftime('%Y-%m-%d %H:%M')})</h1>
    <p>{sum(1 for r in results if r['grade']=='GOOD')} GOOD · {sum(1 for r in results if r['grade']=='PARTIAL')} PARTIAL · {sum(1 for r in results if r['grade']=='NOT RECREATED')} NOT RECREATED of {len(results)} charts.</p>
    <details open><summary>Method</summary><p>Axes are the 2023 workbook formulas (Political Spectrum = 16 signed anchors, Hopscotch = 112-anchor SMB-banking persona, Income, Average Person = single-letter anchors a…3) evaluated as Σ w·Pearson(keyword state z-vector, anchor state z-vector) on today's state-fingerprint plane (944,329 grounded keywords × 51 states) — the same statistic the 2023 charts used. Rows are the exact Tableau groups of the Nov-2023 workbook. Every dot is a live term; hollow = no Google volume measured. Landmarks are dots read off the original slide and checked for the same half of the chart.</p>
    <p>Matrix-h agreement (same formulas as minted <code>audience:saved:*-2023</code> columns, base rows where both exist):</p><ul>{agree}</ul>
    <p>Why not Matrix-first today: the 2023 entity rows sit in the Matrix addendum (row ≥ 2,458,762) and freshly minted pole columns are base-only until the next cycle unions the declared seed columns (artifacts/columns/demo2023_axis_seeds.json, chd_persona_seeds.json, legal_saas_seeds.json) — todo #14723.</p></details>
    {''.join(rows)}"""
    (OUT / "report.html").write_text(html); json.dump(results, open(OUT / "results.json", "w"), default=str, indent=1)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--only", default=""); ap.add_argument("--skip-poi", action="store_true"); ap.add_argument("--no-plot", action="store_true")
    a = ap.parse_args(); eng = Engine(); results = []
    only = {s.strip() for s in a.only.split(",") if s.strip()}
    for spec in CHARTS:
        if only and spec["id"] not in only: continue
        if a.skip_poi and spec.get("rows", {}).get("poi"): continue
        try:
            r = run_chart(spec, eng, not a.no_plot)
        except Exception as e:
            import traceback; traceback.print_exc()
            r = {"id": spec["id"], "slide": spec["slide"], "title": spec["title"], "grade": "NOT RECREATED", "summary": f"error: {type(e).__name__}: {e}", "landmarks": [], "note": spec.get("note", "")}
        results.append(r); print(f"== {r['id']:34s} {r['grade']:14s} {r.get('summary','')}", flush=True)
    write_report(results)

if __name__ == "__main__":
    main()
