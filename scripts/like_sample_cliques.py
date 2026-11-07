"""Share of random English likes going to each category of account, with the liked post as the example.
Reads data/like-sample.json and data/like-sample-tags.json. Writes data/like-sample-cliques.json."""
import json, math, os, random, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(__file__))
from hydrate import add_reply_context, hydrate_posts
random.seed(61)
likes = json.load(open("data/like-sample.json"))
tags = {a["did"]: a for a in json.load(open("data/like-sample-tags.json"))}
cat = lambda d: (tags.get(d) or {}).get("category") or "Not tagged"
n = len(likes); c = Counter(cat(l["did"]) for l in likes)
posts = hydrate_posts(l["uri"] for l in likes)
add_reply_context(posts.values())
by = defaultdict(list)
for l in likes:
    t = tags.get(l["did"]); p = posts.get(l["uri"])
    if t and p:
        acc = next((a for a in by[cat(l["did"])] if a["h"] == t["handle"]), None)   # an account liked more than once gets one entry
        if acc: acc["posts"].append(p)
        else: by[cat(l["did"])].append({"h": t["handle"], "n": t["name"][:40], "f": t["followers"], "s": t.get("summary", ""), "c": t.get("confidence"), "b": t["bio"][:200], "sec": t.get("secondary"), "posts": [p]})
lean = Counter((tags.get(l["did"]) or {}).get("lean", "unknown") for l in likes)
out = {"n_likes": n, "n_accounts": len({l["did"] for l in likes}), "lean": {k: v / n for k, v in lean.items()},
       "cliques": [{"name": k, "like_share": v / n, "moe": 1.96 * math.sqrt((v / n) * (1 - v / n) / n), "likes": v, "sample": random.sample(by[k], min(30, len(by[k])))} for k, v in c.most_common()]}
json.dump(out, open("data/like-sample-cliques.json", "w"))
top = {x["name"]: x["like_share"] for x in json.load(open("data/cliques.json"))["cliques"]}
for x in out["cliques"]: print(f'{x["like_share"]:6.1%} ±{x["moe"]:.1%}   top1000 {top.get(x["name"], 0):6.1%}   {x["name"]}')
print({k: round(v, 3) for k, v in out["lean"].items()})
