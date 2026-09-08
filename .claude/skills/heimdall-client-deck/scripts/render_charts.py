#!/usr/bin/env python3
"""Render the deck's charts from reports/ragnar_deck_data.json in the Genomic Digital house
style (white ground, black type, one amber accent, grey Average band) — the TAB Bank
"Big Data Analysis" scatter grammar: y = correlation with the Ragnar segment, x = political
spectrum, bubble = search volume, every point labelled with its named entity.

Run from the sandbox or the Mac:  python3 render_charts.py <deck_dir>
Writes <deck_dir>/charts/<slug>.png at 300 dpi plus geography.png and disambiguation.png.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

DECK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
# deck dir holds: deck_data.json (from deck_data.py), geomap_states.json (from /api/geomap),
# and optionally disambiguation.json [[anchor, naive, declared], ...] for the methodology chart.
DATA = json.loads((DECK / "deck_data.json").read_text())
GEO = json.loads((DECK / "geomap_states.json").read_text())
SEGMENT_LABEL = DATA.get("segment_label") or "the client segment"
OUT = DECK / "charts"; OUT.mkdir(exist_ok=True)

INK, MUTE, AMBER, GREY, BAND = "#111111", "#8a8a8a", "#E0A100", "#c9c9c9", "#ececec"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": "#bbbbbb",
                     "axes.linewidth": 0.8, "xtick.color": MUTE, "ytick.color": MUTE,
                     "axes.labelcolor": MUTE, "text.color": INK})


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


# Dropped after the qualitative read (2026-09-05): rows with no verifiable volume whose
# value is implausibly large for the category ("new york times" +0.136, "nest thermostat"
# +0.119 — both unvolumed variants of a real row), substitutes that changed the meaning
# ("apple pay wallet", "ring doorbell camera price", "chariots of fire song", "ted lasso
# soundtrack", "college football live", "half marathon training plan 16 weeks"), and the
# zero-volume political-name placeholders whose h is ~0 by construction. Every drop is a
# named decision, not a threshold.
EXCLUDE = {"new york times", "nest thermostat", "apple pay", "ring doorbell", "apple maps", "zelle",
           "chariots of fire", "ted lasso", "half marathon training", "college football", "ncaa basketball",
           "bourbon chase", "ron desantis", "spencer cox", "donald trump", "joe biden", "bernie sanders",
           "planned parenthood", "breitbart", "black lives matter", "baby names", "toddler",
           "obstacle course race", "the way", "running man", "the bear", "samsung galaxy", "chromebook",
           "temu", "iphone", "priceline", "glamping", "park city", "rv rental", "jersey mike's", "sprouts",
           "stanley cup tumbler", "north face", "bass pro shops", "running warehouse", "mint mobile", "pixel phone"}


_exf = DECK / "exclude.json"
if _exf.exists():
    EXCLUDE = set(json.loads(_exf.read_text()))   # this client's named exclusions, with reasons in CHART_AUDIT.md


def scatter(cat, pts, band_lo, band_hi):
    pts = [p for p in pts if p["political"] is not None and p["label"] not in EXCLUDE]
    if len(pts) < 6:
        return None
    fig, ax = plt.subplots(figsize=(8.5, 5.3), dpi=300)
    xs = [p["political"] for p in pts]; ys = [p["segment_h"] for p in pts]
    vols = [max(p["volume"] or 0, 1000) for p in pts]
    sizes = [26 + 14 * math.log10(v) ** 1.6 for v in vols]
    top = sorted(pts, key=lambda p: -p["segment_h"])[:5]
    bottom = sorted(pts, key=lambda p: p["segment_h"])[:3]
    hi = {p["label"] for p in top}; lo = {p["label"] for p in bottom}
    colors = [AMBER if p["label"] in hi else ("#555555" if p["label"] in lo else "#9a9a9a") for p in pts]
    # Average-person band and the political centre band, as in the TAB charts
    ax.axhspan(band_lo, band_hi, color=BAND, zorder=0)
    xr = max(abs(min(xs)), abs(max(xs))) or 0.05
    ax.axvspan(-xr * 0.08, xr * 0.08, color=BAND, zorder=0)
    ax.axhline(0, color="#d0d0d0", lw=0.8, zorder=1)
    ax.scatter(xs, ys, s=sizes, c=colors, alpha=0.85, edgecolors="white", linewidths=0.6, zorder=3)
    texts = []
    for p, x, y in zip(pts, xs, ys):
        w = "bold" if p["label"] in hi else "normal"
        texts.append(ax.text(x, y, p["label"], fontsize=(9.6 if p["label"] in hi else 8.3), weight=w,
                             color=INK if (p["label"] in hi or p["label"] in lo) else "#444444", zorder=4))
    try:
        from adjustText import adjust_text
        adjust_text(texts, ax=ax, expand=(1.15, 1.3), arrowprops=dict(arrowstyle="-", color="#bbbbbb", lw=0.5))
    except Exception:
        pass
    ax.set_xlim(-xr * 1.15, xr * 1.15)
    ax.set_xlabel("← leans left          Political spectrum          leans right →", labelpad=8, fontsize=10)
    ax.set_ylabel(f"Correlation with {SEGMENT_LABEL}", labelpad=8, fontsize=10)
    ax.text(ax.get_xlim()[1], band_hi, "average entity  ", va="bottom", ha="right", fontsize=8, color=MUTE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(False)
    fig.tight_layout()
    f = OUT / f"{slug(cat)}.png"; fig.savefig(f, facecolor="white"); plt.close(fig)
    return f


def geography():
    st = GEO["states"]
    items = sorted(st.items(), key=lambda kv: -kv[1])
    top, bot = items[:12], items[-12:]
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 5.2), dpi=300, sharex=False)
    for ax, data, title, col in ((axes[0], top, "Over-index — where the relay audience lives", AMBER),
                                 (axes[1], bot[::-1], "Under-index — where it does not", "#777777")):
        names = [k.title() for k, _ in data][::-1]; vals = [v for _, v in data][::-1]
        ax.barh(names, vals, color=col, height=0.62)
        ax.set_title(title, loc="left", fontsize=10, color=INK, pad=10)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.tick_params(axis="y", length=0, labelsize=8.5, labelcolor=INK)
        ax.set_xlabel("State z-score of the segment's search fingerprint", fontsize=8)
        for y, v in enumerate(vals):
            ax.text(v + (0.05 if v >= 0 else -0.05), y, f"{v:+.2f}", va="center",
                    ha="left" if v >= 0 else "right", fontsize=7.5, color=MUTE)
    fig.tight_layout(w_pad=3)
    f = OUT / "geography.png"; fig.savefig(f, facecolor="white"); plt.close(fig)
    return f


def disambiguation():
    # [[anchor, naive_word_z, declared_segment_z], ...] measured with ragnar_measure.py-style
    # z-normalised row reads; skipped when the client has no sense collision to show.
    f = DECK / "disambiguation.json"
    if not f.exists():
        return None
    rows = [tuple(r) for r in json.loads(f.read_text())]
    fig, ax = plt.subplots(figsize=(9.6, 5.4), dpi=300)
    y = list(range(len(rows)))[::-1]
    ax.barh([v + 0.19 for v in y], [r[1] for r in rows], height=0.36, color="#bdbdbd", label="Bare brand word")
    ax.barh([v - 0.19 for v in y], [r[2] for r in rows], height=0.36, color=AMBER, label="Declared segment")
    ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows], fontsize=9, color=INK)
    ax.axvline(0, color="#999999", lw=0.8)
    ax.axhspan(2.5, -0.6, color=BAND, zorder=0)
    ax.set_xlabel("Standardised correlation with the anchor (z across 25,798 anchors)", fontsize=8.5)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.legend(frameon=False, loc="lower right", fontsize=8.5)
    fig.tight_layout()
    f = OUT / "disambiguation.png"; fig.savefig(f, facecolor="white"); plt.close(fig)
    return f


def main():
    allpts = [p for pts in DATA["categories"].values() for p in pts
              if p["label"] not in EXCLUDE and p["political"] is not None]
    ys = sorted(p["segment_h"] for p in allpts)
    med = ys[len(ys) // 2]
    q1, q3 = ys[len(ys) // 4], ys[3 * len(ys) // 4]
    band_lo, band_hi = med - (q3 - q1) / 2, med + (q3 - q1) / 2   # the middle half = "average"
    print(f"{len(allpts)} points; median {med:+.4f}; average band {band_lo:+.4f}..{band_hi:+.4f}")
    made = {}
    for cat, pts in DATA["categories"].items():
        f = scatter(cat, pts, band_lo, band_hi)
        made[cat] = str(f) if f else None
        print(f"  {cat:<22} {len(pts):3d} pts -> {f.name if f else 'SKIPPED (thin)'}")
    made["geography"] = str(geography()); _d = disambiguation(); made["disambiguation"] = str(_d) if _d else None
    (OUT / "index.json").write_text(json.dumps({"band": [band_lo, band_hi], "median": med, "charts": made}, indent=1))


if __name__ == "__main__":
    main()
