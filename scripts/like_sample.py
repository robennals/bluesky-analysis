"""Draw a uniform random sample of likes on English posts. Writes data/like-sample.json and the authors' DIDs."""
import json, random
random.seed(51)
liked = [p for p in map(json.loads, open("data/engagement/liked-posts.jsonl")) if ((p.get("langs") or [""])[0] or "").startswith("en")]
likes = [p for p in liked for _ in range(p["w"])]           # each sampled like counts once
sample = random.sample(likes, 1000)
json.dump([{"uri": p["uri"], "did": p["did"]} for p in sample], open("data/like-sample.json", "w"))
dids = sorted({p["did"] for p in sample}); json.dump(dids, open("data/like-sample-dids.json", "w"))
print(len(likes), "English likes in the pool;", len(sample), "drawn;", len(dids), "distinct authors")
