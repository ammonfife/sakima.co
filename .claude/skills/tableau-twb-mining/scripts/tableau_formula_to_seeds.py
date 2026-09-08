#!/usr/bin/env python3
"""Translate Tableau-era Heimdall pole formulas into Heimdall 3.0 signed/weighted seed lists.

Tableau grammar (2020-2023 workbooks):
    ( zn(avg([anchor])-0.17)*3 + zn(avg([other])+0.02) - ((zn(avg([x])) + zn(avg([y]))) / 2) * 5 ) / (20/3.1)
Every formula is LINEAR in the zn(avg([anchor])) terms; the -0.17 offsets and trailing +.042 are constants that
only shift the axis.  So we evaluate the expression symbolically into  {anchor: coefficient} + constant  and emit
Heimdall 3.0 `parse_term` seeds:  'anchor*coef'  /  '-anchor*coef'  (heimdall_core/matrix.py:3943).

Output: defs/audiences_from_tableau.json  — one entry per named calculation with seeds, constant, and provenance.
"""
import json, re, sys, os, math
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = json.load(open(os.path.join(HERE, "defs", "twb_calcs_raw.json")))

TOK = re.compile(r"""
    (?P<ws>\s+|//[^\n]*)                                   # whitespace / line comments
  | (?P<zn>(?:zn|ZN)\s*\(\s*(?:avg|AVG|sum|SUM|min|MIN|max|MAX)\s*\(\s*\[(?P<anchor>[^\]]+)\]\s*\)\s*
        (?:(?P<osign>[-+])\s*(?P<off>\d*\.?\d+))?\s*\))     # zn(avg([X]) - 0.17)
  | (?P<countd>(?:COUNTD|countd|COUNT|count)\s*\(\s*\[[^\]]*\]\s*\))   # countd([keyword]) -> 1
  | (?P<ref>\[(?P<refname>[^\]]+)\])                        # [Calculation_...] reference to another calc
  | (?P<num>\d*\.?\d+)
  | (?P<op>[-+*/()])
  | (?P<func>(?:abs|ABS|sqrt|SQRT|round|ROUND|exp|EXP|sign|SIGN|str|STR|iif|IIF|IF|if)\b)
""", re.X)

class Lin:
    """linear form: coef per anchor + constant"""
    def __init__(self, coefs=None, const=0.0):
        self.c = defaultdict(float, coefs or {}); self.k = const
    def __add__(s, o): r = Lin(dict(s.c), s.k + o.k); [r.c.__setitem__(a, r.c[a] + v) for a, v in o.c.items()]; return r
    def __sub__(s, o): return s + o.scale(-1)
    def scale(s, f): return Lin({a: v * f for a, v in s.c.items()}, s.k * f)
    def is_const(s): return not any(abs(v) > 1e-12 for v in s.c.values())

class Parser:
    def __init__(self, text, resolve):
        self.toks = []; self.resolve = resolve; self.nonlinear = False
        for m in TOK.finditer(text):
            if m.lastgroup == "ws": continue
            self.toks.append(m)
        self.i = 0
    def peek(self): return self.toks[self.i] if self.i < len(self.toks) else None
    def take(self): t = self.toks[self.i]; self.i += 1; return t
    def expr(self):
        v = self.term()
        while (t := self.peek()) and t.group("op") in ("+", "-"):
            self.take(); r = self.term(); v = v + r if t.group("op") == "+" else v - r
        return v
    def term(self):
        v = self.factor()
        while (t := self.peek()) and t.group("op") in ("*", "/"):
            self.take(); r = self.factor()
            if t.group("op") == "*":
                if r.is_const(): v = v.scale(r.k)
                elif v.is_const(): v = r.scale(v.k)
                else: self.nonlinear = True; v = v + r     # product of two poles: not linear, keep union
            else:
                if r.is_const() and abs(r.k) > 1e-12: v = v.scale(1.0 / r.k)
                else: self.nonlinear = True
        return v
    def factor(self):
        t = self.peek()
        if t is None: return Lin()
        g = t.lastgroup
        if g == "op" and t.group("op") == "-": self.take(); return self.factor().scale(-1)
        if g == "op" and t.group("op") == "+": self.take(); return self.factor()
        if g == "op" and t.group("op") == "(":
            self.take(); v = self.expr()
            if (p := self.peek()) and p.group("op") == ")": self.take()
            return v
        if g == "num": self.take(); return Lin({}, float(t.group("num")))
        if g == "zn":
            self.take(); off = 0.0
            if t.group("off"): off = float(t.group("off")) * (1 if t.group("osign") == "+" else -1)
            return Lin({t.group("anchor").strip(): 1.0}, off)
        if g == "countd": self.take(); return Lin({}, 1.0)
        if g == "ref":
            self.take(); sub = self.resolve(t.group("refname"))
            return sub if sub is not None else Lin({"__ref:" + t.group("refname"): 1.0})
        if g == "func":
            self.take()          # abs()/sqrt()/... wrap: treat as identity on the linear form, flag nonlinear
            self.nonlinear = True
            if (p := self.peek()) and p.group("op") == "(":
                self.take(); v = self.expr()
                # swallow extra args (round(x,2))
                depth = 1
                while (p := self.peek()) and depth:
                    if p.group("op") == "(": depth += 1
                    elif p.group("op") == ")": depth -= 1
                    self.take()
                return v
            return Lin()
        self.take(); return Lin()

def translate(workbook):
    calcs = RAW[workbook]["calcs"]
    byname = {k: v for k, v in calcs.items()}
    cache = {}
    def resolve(ref):
        key = "[" + ref + "]"
        if key in cache: return cache[key]
        v = byname.get(key)
        if v is None: return None
        cache[key] = Lin()        # cycle guard
        p = Parser(v["formula"], resolve); lin = p.expr(); cache[key] = lin
        return lin
    out = {}
    for key, v in calcs.items():
        f = v["formula"]
        if "zn(" not in f.lower() and "[Calculation" not in f and "(copy)" not in f: continue
        p = Parser(f, resolve); lin = p.expr()
        if lin.is_const(): continue
        coefs = {a: c for a, c in lin.c.items() if abs(c) > 1e-9}
        if not coefs: continue
        # normalise so max |coef| == 1 (Heimdall fold is a weighted SUM; scale is irrelevant to the ordering)
        mx = max(abs(c) for c in coefs.values())
        seeds = []
        for a, c in sorted(coefs.items(), key=lambda kv: -abs(kv[1])):
            w = round(c / mx, 4)
            if a.startswith("__ref:"): seeds.append({"term": a, "weight": w, "unresolved_ref": True}); continue
            s = ("-" if w < 0 else "") + a + ("" if abs(abs(w) - 1) < 1e-9 else f"*{abs(w)}")
            seeds.append({"term": a, "weight": w, "seed": s})
        out[v["caption"] or key] = {
            "tableau_name": key, "workbook": workbook, "role": v["role"], "datatype": v["datatype"],
            "n_anchors": len(coefs), "n_positive": sum(1 for s in seeds if s["weight"] > 0),
            "n_negative": sum(1 for s in seeds if s["weight"] < 0),
            "constant": round(lin.k, 4), "nonlinear_parts": p.nonlinear,
            "seeds": seeds, "heimdall_terms": [s["seed"] for s in seeds if "seed" in s],
            "formula": f.strip(),
        }
    return out

if __name__ == "__main__":
    books = sys.argv[1:] or ["Heimdall Nov 2023_Hopscotch.twb"]
    allout = {}
    for b in books:
        t = translate(b); allout[b] = t
        print(f"{b}: {len(t)} linear pole definitions", file=sys.stderr)
    json.dump(allout, open(os.path.join(HERE, "defs", "audiences_from_tableau.json"), "w"), indent=1, ensure_ascii=False)
    for b, t in allout.items():
        for name, d in t.items():
            print(f"{name:45s} anchors={d['n_anchors']:3d} +{d['n_positive']:3d} -{d['n_negative']:3d} nonlin={d['nonlinear_parts']}  {d['heimdall_terms'][:4]}")
