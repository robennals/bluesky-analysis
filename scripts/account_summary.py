"""Summarize 30-day likes per account for the random sample of active accounts.

Accounts were drawn from everyone who posted during the sample, so frequent posters were more likely to be drawn.
The weighted figures correct for this by weighting each account by 1 / (its posts in the sample).
Writes data/account-likes-summary.json."""
import glob, json
from collections import Counter
import numpy as np

english = set(json.load(open("data/english-accounts.json")))
rows = [r for r in map(json.loads, open("data/graph/account-likes.jsonl")) if "error" not in r and r["did"] in english]
inc = Counter(json.loads(l)["did"] for f in glob.glob("data/slots/posts-*.jsonl") for l in open(f))
L = np.array([r["likes"] for r in rows], float); P = np.array([r["posts"] for r in rows], float)
W = np.array([1 / max(inc[r["did"]], 1) for r in rows])
fol = {p["did"]: p.get("followersCount") or 0 for p in map(json.loads, open("data/graph/profiles.jsonl"))}
F = np.array([fol.get(r["did"], 0) for r in rows], float)

def summary(weights):
    o = np.argsort(-L); l, w = L[o], weights[o]
    cw, cl = np.cumsum(w) / w.sum(), np.cumsum(l * w) / (l * w).sum()
    at = lambda f: float(cl[np.searchsorted(cw, f)])
    def q(p): return float(np.sort(L)[np.searchsorted(np.cumsum(weights[np.argsort(L)]) / weights.sum(), p)])
    bins = [("0", 0, 1), ("1–9", 1, 10), ("10–99", 10, 100), ("100–999", 100, 1000), ("1K–10K", 1000, 10000), ("10K+", 10000, 1e12)]
    return {"top_share": {str(f): at(f) for f in (0.001, 0.01, 0.1, 0.5)}, "median": q(.5), "p90": q(.9), "p99": q(.99),
            "mean": float((L * weights).sum() / weights.sum()), "zero": float(weights[L == 0].sum() / weights.sum()),
            "curve": [[float(x), at(x)] for x in np.unique(np.concatenate([np.logspace(-4, 0, 50), np.linspace(0.01, 1, 100)])) if x < 0.999] + [[1.0, 1.0]],
            "hist": [[lab, float(weights[(L >= a) & (L < b)].sum() / weights.sum())] for lab, a, b in bins]}
s = {"n": len(rows), "capped": sum(r["capped"] for r in rows), "weighted": summary(W), "unweighted": summary(np.ones(len(rows))),
     "corr_log_followers_likes": float(np.corrcoef(np.log1p(F), np.log1p(L))[0, 1]),
     "corr_log_posts_likes": float(np.corrcoef(np.log1p(P), np.log1p(L))[0, 1]),
     "median_posts": float(np.median(P)), "no_posts_30d": float((P == 0).mean())}
json.dump(s, open("data/account-likes-summary.json", "w"), indent=1)
print(json.dumps({k: v for k, v in s.items() if k not in ("weighted", "unweighted")}))
for k in ("weighted", "unweighted"):
    print(k, {x: y for x, y in s[k].items() if x != "curve"})
