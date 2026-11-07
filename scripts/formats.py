"""Post formats: share of posts and share of likes, split by top-level posts vs replies. Mutually exclusive buckets.
Likes are lifetime counts on sampled posts at least 12 hours old. Writes data/formats.json."""
import glob, json, os, re, time
from collections import defaultdict
import numpy as np

posts = [p for f in glob.glob("data/slots/posts-*.jsonl") for p in map(json.loads, open(f)) if ((p.get("langs") or [""])[0] or "").startswith("en")]
counts = {}
for l in open("data/graph/post-counts.tsv"):
    u, lk, *_ = l.rstrip("\n").split("\t"); counts[u] = int(lk)
cut = os.path.getmtime("data/graph/post-counts.tsv") - 12 * 3600
from post_format import fmt

rows = defaultdict(lambda: {"posts": 0, "top": 0, "reply": 0, "likes": 0, "likes_top": 0, "counted": 0, "vals": []})
n_all = 0
for p in posts:
    n_all += 1; f = fmt(p); r = rows[f]; r["posts"] += 1; r["reply" if p["reply"] else "top"] += 1
    u = f"at://{p['did']}/app.bsky.feed.post/{p['rkey']}"
    if u in counts and time.mktime(time.strptime(p["t"][:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone < cut:
        r["counted"] += 1; r["likes"] += counts[u]; r["vals"].append(counts[u]); r["likes_top"] += 0 if p["reply"] else counts[u]
tl = sum(r["likes"] for r in rows.values()); tc = sum(r["counted"] for r in rows.values())
out = []
for k, r in rows.items():
    v = np.array(r["vals"] or [0])
    out.append({"format": k, "posts": r["posts"], "share_posts": r["counted"] / tc, "share_likes": r["likes"] / tl,
                "reply_share": r["reply"] / r["posts"], "mean": float(v.mean()), "median": float(np.median(v)), "zero": float((v == 0).mean())})
out.sort(key=lambda r: -r["share_posts"])
tp = [p for p in posts if not p["reply"]]
extra = {"n": n_all, "counted": tc, "reply_share": 1 - len(tp) / n_all, "hashtag_share": sum(bool(p.get("tags")) for p in posts) / n_all,
         "likes_on_replies": sum(counts.get(f"at://{p['did']}/app.bsky.feed.post/{p['rkey']}", 0) for p in posts if p["reply"]) / sum(counts.get(f"at://{p['did']}/app.bsky.feed.post/{p['rkey']}", 0) for p in posts)}
json.dump({"rows": out, "extra": extra}, open("data/formats.json", "w"), indent=1)
print(f"{'format':28} posts  likes  ratio  mean med  zero  replies")
for r in out: print(f"{r['format']:28} {r['share_posts']:5.1%} {r['share_likes']:6.1%} {r['share_likes']/r['share_posts']:5.2f}x {r['mean']:6.1f} {r['median']:3.0f} {r['zero']:4.0%} {r['reply_share']:6.0%}")
print(extra)
