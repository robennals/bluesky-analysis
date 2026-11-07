"""Collect (1) like/repost counts for the sampled posts, (2) profiles of every sampled poster,
(3) the full follow lists of a random sample of active accounts. Writes to data/graph/.

Usage: python3 collect_graph.py <n_follow_sample>
"""
import glob, json, os, random, sys, time
from concurrent.futures import ThreadPoolExecutor
from bsky import call, paginate

N = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
OUT = "../data/graph"; os.makedirs(OUT, exist_ok=True)
posts = [json.loads(l) for f in sorted(glob.glob("../data/slots/posts-*.jsonl")) for l in open(f)]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)

# 1. Engagement counts for every sampled post (getPosts takes 25 URIs).
uris = [f"at://{p['did']}/app.bsky.feed.post/{p['rkey']}" for p in posts]
def counts(batch):
    try: return [(p["uri"], p.get("likeCount", 0), p.get("repostCount", 0), p.get("replyCount", 0), p.get("quoteCount", 0))
                 for p in call("app.bsky.feed.getPosts", uris=batch)["posts"]]
    except Exception: return []
if not os.path.exists(f"{OUT}/post-counts.tsv"):
    with ThreadPoolExecutor(4) as ex, open(f"{OUT}/post-counts.tsv", "w") as f:
        for i, rows in enumerate(ex.map(counts, [uris[i:i+25] for i in range(0, len(uris), 25)])):
            for r in rows: f.write("\t".join(map(str, r)) + "\n")
            if i % 500 == 0: log("post counts batch", i)
log("post counts done")

# 2. Profiles of every sampled poster (followers, follows, posts, account age).
dids = sorted({p["did"] for p in posts})
def profs(batch):
    try: return call("app.bsky.actor.getProfiles", actors=batch)["profiles"]
    except Exception: return []
if not os.path.exists(f"{OUT}/profiles.jsonl"):
    with ThreadPoolExecutor(4) as ex, open(f"{OUT}/profiles.jsonl", "w") as f:
        for rows in ex.map(profs, [dids[i:i+25] for i in range(0, len(dids), 25)]):
            for p in rows:
                f.write(json.dumps({k: p.get(k) for k in ("did", "handle", "displayName", "description", "followersCount",
                                                           "followsCount", "postsCount", "createdAt")}) + "\n")
log("profiles done:", len(dids))

# 3. Follow lists of a random sample of active (posting) accounts.
random.seed(42)
sample = random.sample(dids, min(N, len(dids)))
done = {l.split("\t", 1)[0] for l in open(f"{OUT}/follows.tsv")} if os.path.exists(f"{OUT}/follows.tsv") else set()
def follows(d):
    try: return d, [f["did"] for f in paginate("app.bsky.graph.getFollows", "follows", max_items=5000, actor=d)]
    except Exception: return d, None
with ThreadPoolExecutor(4) as ex, open(f"{OUT}/follows.tsv", "a") as f:
    for i, (d, fs) in enumerate(ex.map(follows, [d for d in sample if d not in done])):
        if fs is not None: f.write(d + "\t" + ",".join(fs) + "\n")
        if i % 100 == 0: log("follow lists", i)
log("follow sample done")
