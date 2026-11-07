"""Rebuild attention stats on 30 days of likes, from the stratified account sample.

Population: accounts seen posting or being liked in the sampled windows, English (at least half their recent posts), with
a post in the last 30 days. Weights undo the oversampling of the most-liked accounts. Writes data/attention.json (same
shape as attention_compare.py), data/account-likes-summary.json, data/top-accounts.json and data/cliques.json.
"""
import glob, json, os, random, re, sys, time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from model2vec import StaticModel
sys.path.insert(0, os.path.dirname(__file__))
from bsky import call
from hydrate import _example, account_cards, add_reply_context
from post_format import fmt

random.seed(41)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
DROP = "Non-English posts"; TOP01 = "Top 0.1%"; GROUPS = ["Top 1%", "Next 9%", "Other 90%"]
FMT = {"Video": "Video", "Images with text": "Images", "Images, no text": "Images", "Quote post with media": "Quote with media", "Quote post": "Quote post",
       "Link card": "Link", "Text with bare link": "Link", "GIF": "GIF"}
URL = re.compile(r"https?://\S+|\b\S+\.(com|org|net|io|social|app|gg|co|uk|jp)/\S*")
clean = lambda t: " ".join(URL.sub(" ", t or "").split())

meta = json.load(open("data/graph/strat-meta.json"))
rows = [r for r in map(json.loads, open("data/graph/account-likes-strat.jsonl")) if "error" not in r and r["posts"] > 0]
tail_done = sum(r["stratum"] == "tail" for r in rows)
for r in rows: r["w"] = 1.0 if r["stratum"] == "head" else meta["tail_population"] / tail_done   # the unfinished tail was a random remainder
rows = [r for r in rows if r["en"] / r["posts"] >= 0.5]
rows.sort(key=lambda r: -r["likes"])
L = np.array([r["likes"] for r in rows], float); W = np.array([r["w"] for r in rows]); P = np.array([r["posts"] for r in rows], float)
N = W.sum(); cw = np.cumsum(W) / N; cl = np.cumsum(L * W) / (L * W).sum()
log(f"{len(rows)} accounts, estimated population {N:,.0f}; capped {sum(r['capped'] for r in rows)}")
share_at = lambda f: float(cl[min(np.searchsorted(cw, f), len(cl) - 1)])
def q(v, w, p):
    o = np.argsort(v); c = np.cumsum(w[o]) / w.sum(); return float(v[o][min(np.searchsorted(c, p), len(v) - 1)])
grid = np.unique(np.concatenate([np.logspace(-4, 0, 50), np.linspace(0.01, 1, 100)]))
json.dump({"n": len(rows), "population": N, "capped": sum(r["capped"] for r in rows), "weighted": {"top_share": {str(f): share_at(f) for f in (0.001, 0.01, 0.1, 0.5)}, "median": q(L, W, .5), "p90": q(L, W, .9), "p99": q(L, W, .99),
           "mean": float((L * W).sum() / W.sum()), "zero": float(W[L == 0].sum() / W.sum()), "curve": [[float(x), share_at(x)] for x in grid if x < 0.999] + [[1.0, 1.0]]}}, open("data/account-likes-summary.json", "w"))
# top-k accounts by estimated rank
def top_k(k):
    i = np.searchsorted(np.cumsum(W), k); return float(cl[min(i, len(cl) - 1)]), int(i)
tk = {str(k): top_k(k)[0] for k in (100, 1000, 10000)}
json.dump({"top_by_likes": tk, "accounts": N}, open("data/top-accounts.json", "w"))
log("top-k shares", tk)

# groups
frac = cw
group = {}
for r, f in zip(rows, frac): group[r["did"]] = GROUPS[0] if f <= 0.01 else GROUPS[1] if f <= 0.10 else GROUPS[2]
top01 = {r["did"] for r, f in zip(rows, frac) if f <= 0.001}
dids = [r["did"] for r in rows]; prof = {}
for i in range(0, len(dids), 25):
    for p in call("app.bsky.actor.getProfiles", actors=dids[i:i+25])["profiles"]: prof[p["did"]] = p
def feed(d):
    try: return d, [i["post"] for i in call("app.bsky.feed.getAuthorFeed", actor=d, limit=40, filter="posts_with_replies")["feed"] if "reason" not in i]
    except Exception: return d, []
with ThreadPoolExecutor(3) as ex: feeds = dict(ex.map(feed, dids))
log("feeds", len(feeds))
st = json.load(open("data/topics-stage1.json")); cent = np.array(st["centroids"]); cat = {c["id"]: c["category"] for c in st["clusters"]}
model = StaticModel.from_pretrained("data/models/potion-base-32M")
items = [(d, x) for d, v in feeds.items() for x in v if ((x["record"].get("langs") or [""])[0] or "").startswith("en")]
tx = [(d, x) for d, x in items if len(clean(x["record"].get("text"))) >= 15]
X = model.encode([clean(x["record"].get("text")) for _, x in tx], show_progress_bar=False); nr = np.linalg.norm(X, axis=1); ok = nr > 1e-6
lab = ((X[ok] / nr[ok, None]) @ cent.T).argmax(1); cats = {x["uri"]: cat[int(c)] for (_, x), c, k in zip([t for t, o in zip(tx, ok) if o], lab, [True] * int(ok.sum()))}
def post_fmt(x):
    e = x["record"].get("embed") or {}; ext = e.get("external") or (e.get("media") or {}).get("external") or {}
    return FMT.get(fmt({"embed": e.get("$type"), "ext": ext.get("uri"), "text": x["record"].get("text")}), "Text")
wt = {r["did"]: r["w"] for r in rows}
members = lambda g: top01 if g == TOP01 else {d for d in dids if group[d] == g}
out = {"n_accounts": N, "n_sampled": len(rows), "groups": GROUPS, "stats": {}, "topics": {}, "formats": {}, "pools": {}, "accounts": {}}
pool = defaultdict(list)
for g in [TOP01] + GROUPS:
    ms = members(g); idx = np.array([r["did"] in ms for r in rows]); w = W[idx]; rr = [r for r in rows if r["did"] in ms]
    f = lambda k: np.array([prof.get(r["did"], {}).get(k) or 0 for r in rr], float)
    age = np.array([(time.time() - time.mktime(time.strptime((prof.get(r["did"], {}).get("createdAt") or "2024-01-01")[:10], "%Y-%m-%d"))) / 86400 / 365.25 for r in rr])
    out["stats"][g] = {"accounts": float(w.sum()), "sampled": len(rr), "like_share": float((L[idx] * w).sum() / (L * W).sum()), "post_share": float((P[idx] * w).sum() / (P * W).sum()), "median_followers": q(f("followersCount"), w, .5), "median_follows": q(f("followsCount"), w, .5),
                       "median_total_posts": q(f("postsCount"), w, .5), "median_age_years": q(age, w, .5), "reply_share": float(sum(r["replies"] * r["w"] for r in rr) / sum(r["posts"] * r["w"] for r in rr)), "likes_per_account": float((L[idx] * w).sum() / w.sum()), "posts_30d": q(P[idx], w, .5)}
    tc, fc = Counter(), Counter()
    for d in ms:
        for x in feeds.get(d, []):
            if not ((x["record"].get("langs") or [""])[0] or "").startswith("en"): continue
            fm = post_fmt(x); fc[fm] += wt[d]; ct = cats.get(x["uri"])
            if ct and ct != DROP: tc[ct] += wt[d]; pool[("cat", g, ct)].append(x)
            pool[("fmt", g, fm)].append(x)
    out["topics"][g] = {k: v / sum(tc.values()) for k, v in tc.items()}; out["formats"][g] = {k: v / sum(fc.values()) for k, v in fc.items()}
    acc = random.sample(sorted(ms), min(20, len(ms))); cards = account_cards(acc); out["accounts"][g] = [cards[d] for d in acc if d in cards]
out["pools"] = {"|".join(k): [_example(x) for x in random.sample(v, min(12, len(v)))] for k, v in pool.items()}
add_reply_context([e for v in out["pools"].values() for e in v])
json.dump(out, open("data/attention.json", "w"), separators=(",", ":"))
for g in [TOP01] + GROUPS: print(g, json.dumps({k: round(v, 3) for k, v in out["stats"][g].items()}))

# cliques among the top 1,000 by 30-day likes
tags = {a["did"]: a for a in json.load(open("data/top-accounts-tags.json")) if a.get("category")}
top = [r for r in rows if r["stratum"] == "head" and r["did"] in tags][:1000]
outside = sum(r["w"] for r in rows if r["stratum"] == "tail" and r["likes"] >= top[-1]["likes"])
tot = sum(r["likes"] for r in top); byc = defaultdict(list)
for r in top: byc[tags[r["did"]]["category"]].append(r)
cards = [{"name": k, "accounts": len(v), "account_share": len(v) / len(top), "like_share": sum(r["likes"] for r in v) / tot,
          "sample": [{"h": tags[r["did"]]["handle"], "n": tags[r["did"]]["name"][:40], "f": tags[r["did"]]["followers"], "s": tags[r["did"]].get("summary", ""), "c": tags[r["did"]].get("confidence"), "l": r["likes"], "b": tags[r["did"]]["bio"][:200], "sec": tags[r["did"]].get("secondary"), "posts": [_example(x) for x in sorted(feeds.get(r["did"], []), key=lambda x: -x.get("likeCount", 0))[:8]]} for r in sorted(v, key=lambda r: -r["likes"])[:30]]} for k, v in byc.items()]  # most-liked first
cards.sort(key=lambda c: -c["like_share"])
add_reply_context([p for c in cards for a in c["sample"] for p in a["posts"]])
lean = Counter(); [lean.update({tags[r["did"]].get("lean", "none"): r["likes"]}) for r in top]
json.dump({"n": len(top), "threshold": top[-1]["likes"], "estimated_outside": outside, "top_share_of_all": float(sum(r["likes"] * r["w"] for r in top) / (L * W).sum()), "lean": {k: v / tot for k, v in lean.items()}, "cliques": cards}, open("data/cliques.json", "w"))
print("top1000 share of likes", round(sum(r["likes"] * r["w"] for r in top) / (L * W).sum(), 3), "threshold", top[-1]["likes"], "tail accounts est above", round(outside)); print({k: round(v, 3) for k, v in sorted({k: v / tot for k, v in lean.items()}.items())})
for c in cards: print(f'{c["like_share"]:5.1%} {c["accounts"]:4} {c["name"]}')
