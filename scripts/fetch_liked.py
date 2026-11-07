"""Draw a uniform random sample of likes from the engagement replay and fetch the liked posts.
Each sampled like is one 'vote', so the fetched posts (weighted by sample count) show what gets attention."""
import glob, json, random, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from bsky import call

N = 30000
likes = [l.rstrip("\n").split("\t")[2] for f in glob.glob("../data/engagement/eng-*.tsv") for l in open(f) if l.startswith("like\t")]
random.seed(7)
sample = Counter(random.sample(likes, N))
uris = [u for u in sample if "/app.bsky.feed.post/" in u]
def get(batch):
    try: return call("app.bsky.feed.getPosts", uris=batch)["posts"]
    except Exception: return []
out = open("../data/engagement/liked-posts.jsonl", "w")
with ThreadPoolExecutor(3) as ex:
    for i, ps in enumerate(ex.map(get, [uris[i:i+25] for i in range(0, len(uris), 25)])):
        for p in ps:
            r = p["record"]; e = (p.get("embed") or {})
            ext = (e.get("external") or (e.get("media") or {}).get("external") or {})
            out.write(json.dumps({"uri": p["uri"], "did": p["author"]["did"], "handle": p["author"]["handle"],
                "text": r.get("text", ""), "langs": r.get("langs"), "reply": bool(r.get("reply")),
                "embed": e.get("$type", "").replace("#view", ""), "extTitle": ext.get("title"),
                "w": sample[p["uri"]], "likeCount": p.get("likeCount", 0), "t": r.get("createdAt")}) + "\n")
        if i % 200 == 0: print(time.strftime("%H:%M:%S"), i, flush=True)
print("done", len(uris), "distinct liked posts from", N, "sampled likes")
