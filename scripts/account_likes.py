"""Likes received per account over the last 30 days, for the random sample of active accounts in data/graph/follows.tsv.
Counts every original post and reply (not reposts). Writes data/graph/account-likes.jsonl (resumable)."""
import json, os, time
from concurrent.futures import ThreadPoolExecutor
from bsky import call

G = "../data/graph"; OUT = f"{G}/account-likes.jsonl"
SINCE = "2026-09-30"; MAX_PAGES = 12
users = [l.split("\t", 1)[0] for l in open(f"{G}/follows.tsv") if "\t" in l]
done = {json.loads(l)["did"] for l in open(OUT)} if os.path.exists(OUT) else set()
def one(d):
    posts = likes = replies = 0; maxl = 0; cursor = None; capped = False
    try:
        for page in range(MAX_PAGES):
            r = call("app.bsky.feed.getAuthorFeed", actor=d, limit=100, filter="posts_with_replies", cursor=cursor)
            items = r.get("feed", [])
            stop = False
            for i in items:
                if "reason" in i: continue
                p = i["post"]
                if p["record"].get("createdAt", "") < SINCE:
                    stop = True; continue
                n = p.get("likeCount", 0); posts += 1; likes += n; maxl = max(maxl, n); replies += bool(i.get("reply"))
            cursor = r.get("cursor")
            if stop or not cursor or not items: break
        else: capped = True
    except Exception as e:
        return {"did": d, "error": str(e)[:100]}
    return {"did": d, "posts": posts, "likes": likes, "replies": replies, "max": maxl, "capped": capped}
with ThreadPoolExecutor(4) as ex, open(OUT, "a") as f:
    for n, r in enumerate(ex.map(one, [u for u in users if u not in done])):
        f.write(json.dumps(r) + "\n"); f.flush()
        if n % 200 == 0: print(time.strftime("%H:%M:%S"), n, flush=True)
print("done")
