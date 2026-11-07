"""English-only versions of the concentration stats, plus the language breakdown. Writes data/english-stats.json.
A post is English if its first language tag is en. An account is English if at least half its sampled posts are."""
import glob, json, os, time
from collections import Counter
import numpy as np

NAMES = {"en": "English", "?": "No language tag", "ja": "Japanese", "pt": "Portuguese", "es": "Spanish", "de": "German", "fr": "French", "ne": "Nepali", "ko": "Korean", "nl": "Dutch", "ru": "Russian", "it": "Italian", "zh": "Chinese", "tr": "Turkish", "ar": "Arabic"}
lang = lambda p: ((p.get("langs") or ["?"])[0] or "?").split("-")[0]
posts = [json.loads(l) for f in glob.glob("data/slots/posts-*.jsonl") for l in open(f)]
liked = [json.loads(l) for l in open("data/engagement/liked-posts.jsonl")]
lp, ll = Counter(lang(p) for p in posts), Counter()
for p in liked: ll[lang(p)] += p["w"]
tp, tl = sum(lp.values()), sum(ll.values())
top = [k for k, _ in lp.most_common(9)]
rows = [{"code": k, "name": NAMES.get(k, k), "posts": lp[k] / tp, "likes": ll[k] / tl} for k in top]
rows.append({"code": "other", "name": "Other languages", "posts": 1 - sum(r["posts"] for r in rows), "likes": 1 - sum(r["likes"] for r in rows)})

# English-only like distribution
counts = {}
for l in open("data/graph/post-counts.tsv"):
    u, lk, *_ = l.rstrip("\n").split("\t"); counts[u] = int(lk)
cut = os.path.getmtime("data/graph/post-counts.tsv") - 12 * 3600
vals = []
for p in posts:
    u = f"at://{p['did']}/app.bsky.feed.post/{p['rkey']}"
    if lang(p) == "en" and u in counts and time.mktime(time.strptime(p["t"][:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone < cut: vals.append(counts[u])
old = np.sort(np.array(vals))[::-1]; t = old.sum()
like_dist = {"n_posts": int(len(old)), "total_likes": int(t), "zero": float((old == 0).mean()), "median": float(np.median(old)), "mean": float(old.mean()),
             "top_share": {str(f): float(old[: max(1, int(len(old) * f))].sum() / t) for f in (0.001, 0.01, 0.1)},
             "curve": [[float(x), float(old[: max(1, int(len(old) * x))].sum() / t)] for x in np.unique(np.concatenate([np.logspace(-4, 0, 50), np.linspace(0.01, 1, 100)]))],
             "hist": [[lab, int(((old >= a) & (old < b)).sum())] for lab, a, b in [("0", 0, 1), ("1", 1, 2), ("2–4", 2, 5), ("5–9", 5, 10), ("10–99", 10, 100), ("100–999", 100, 1000), ("1,000+", 1000, 10**9)]]}

# English accounts
n, en = Counter(), Counter()
for p in posts: n[p["did"]] += 1; en[p["did"]] += lang(p) == "en"
english = {d for d in n if en[d] / n[d] >= 0.5}
json.dump(sorted(english), open("data/english-accounts.json", "w"))
lists = []
for l in open("data/graph/follows.tsv"):
    if "\t" in l and l.endswith("\n"):
        d, fs = l.rstrip("\n").split("\t")
        if d in english: lists.append([x for x in fs.split(",") if x])
indeg = Counter(x for fs in lists for x in fs); edges = sum(indeg.values()); ranked = [v for _, v in indeg.most_common()]
cum = np.cumsum(ranked) / edges
fc = np.array([p.get("followersCount") or 0 for p in map(json.loads, open("data/graph/profiles.jsonl")) if p["did"] in english])
bins = [0, 1, 10, 100, 1000, 10000, 100000, 1e9]; srt = np.sort(fc)[::-1]
graph = {"sample_users": len(lists), "edges": edges, "distinct_targets": len(indeg), "median_follows": float(np.median([len(f) for f in lists])),
         "top_share": {str(k): float(cum[k - 1]) for k in (10, 100, 1000, 10000)}, "followed_by_1": sum(v == 1 for v in ranked) / len(ranked),
         "edge_curve": [[float(x), float(cum[max(0, int(x * len(ranked)) - 1)])] for x in np.unique(np.concatenate([np.logspace(-4, 0, 50), np.linspace(0.01, 1, 100)]))],
         "followers_pct": {str(q): float(np.percentile(fc, q)) for q in (10, 25, 50, 75, 90, 99, 99.9)},
         "followers_hist": [[str(i), int(((fc >= bins[i]) & (fc < bins[i + 1])).sum())] for i in range(len(bins) - 1)],
         "followers_top1pct_share": float(srt[: len(srt) // 100].sum() / srt.sum())}
json.dump({"languages": rows, "like_dist": like_dist, "graph": graph, "english_share_accounts": len(english) / len(n)}, open("data/english-stats.json", "w"))
print("languages", [(r["name"], round(r["posts"], 3), round(r["likes"], 3)) for r in rows])
print("EN likes: zero", round(like_dist["zero"], 3), like_dist["top_share"], "n", like_dist["n_posts"])
print("EN accounts", len(english), "of", len(n), "| follow sample", len(lists), "top1000", round(graph["top_share"]["1000"], 3), "by1", round(graph["followed_by_1"], 3), "median followers", graph["followers_pct"]["50"])
