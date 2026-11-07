"""30-day likes for a stratified sample of accounts, so accounts can be ranked on 30 days rather than a 34-minute window.

Population: every account that posted or was liked during the sampled windows. Strata: the 1,500 most-liked accounts in
the windows (all taken), plus 1,500 random others. Records sampling weight, and English share so language can be filtered.
Writes data/graph/account-likes-strat.jsonl (resumable).
"""
import glob, json, os, random, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from bsky import call

G = "../data/graph"; OUT = f"{G}/account-likes-strat.jsonl"; SINCE = "2026-09-30"; MAX_PAGES = 12
likes = Counter()
for f in glob.glob("../data/engagement/eng-*.tsv"):
    for l in open(f):
        k, _, t = l.rstrip("\n").split("\t")
        if k == "like" and "/app.bsky.feed.post/" in t: likes[t.split("/")[2]] += 1
population = set(likes) | {json.loads(l)["did"] for f in glob.glob("../data/slots/posts-*.jsonl") for l in open(f)}
head = [d for d, _ in likes.most_common(1500)]
random.seed(31); tail = sorted(population - set(head)); rest = random.sample(tail, 1500)
weight = {**{d: 1.0 for d in head}, **{d: len(tail) / 1500 for d in rest}}
json.dump({"population": len(population), "head": len(head), "tail_population": len(tail)}, open(f"{G}/strat-meta.json", "w"))
done = {json.loads(l)["did"] for l in open(OUT)} if os.path.exists(OUT) else set()
def one(d):
    posts = lk = rep = en = 0; maxl = 0; cursor = None; capped = False
    try:
        for page in range(MAX_PAGES):
            r = call("app.bsky.feed.getAuthorFeed", actor=d, limit=100, filter="posts_with_replies", cursor=cursor)
            items = r.get("feed", []); stop = False
            for i in items:
                if "reason" in i: continue
                p = i["post"]; rec = p["record"]
                if rec.get("createdAt", "") < SINCE: stop = True; continue
                n = p.get("likeCount", 0); posts += 1; lk += n; maxl = max(maxl, n); rep += bool(i.get("reply")); en += ((rec.get("langs") or [""])[0] or "").startswith("en")
            cursor = r.get("cursor")
            if stop or not cursor or not items: break
        else: capped = True
    except Exception as e:
        return {"did": d, "w": weight[d], "error": str(e)[:100]}
    return {"did": d, "w": weight[d], "stratum": "head" if d in set(head[:0]) or weight[d] == 1.0 else "tail", "posts": posts, "likes": lk, "replies": rep, "en": en, "max": maxl, "capped": capped}
with ThreadPoolExecutor(4) as ex, open(OUT, "a") as f:
    for n, r in enumerate(ex.map(one, [d for d in head + rest if d not in done])):
        f.write(json.dumps(r) + "\n"); f.flush()
        if n % 200 == 0: print(time.strftime("%H:%M:%S"), n, flush=True)
print("done")
