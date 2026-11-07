"""Share of likes going to the top 1,000 accounts, by likes received and by follows. Writes data/top-accounts.json.
Likes are every like in the 34 minutes of sampled windows, so this measures who is being liked right now."""
import glob, json
from collections import Counter
is_en = lambda p: ((p.get("langs") or [""])[0] or "").startswith("en")
likes = Counter()
for f in glob.glob("data/engagement/eng-*.tsv"):
    for l in open(f):
        k, _, t = l.rstrip("\n").split("\t")
        if k == "like" and "/app.bsky.feed.post/" in t: likes[t.split("/")[2]] += 1
english = set(json.load(open("data/english-accounts.json")))
en, tot = Counter(), Counter()
for p in map(json.loads, open("data/engagement/liked-posts.jsonl")): tot[p["did"]] += p["w"]; en[p["did"]] += p["w"] * is_en(p)
for d in tot:
    if en[d] / tot[d] >= 0.5: english.add(d)
    else: english.discard(d)
all_total = sum(likes.values())
en_likes = {d: n for d, n in likes.items() if d in english}
t = sum(en_likes.values()); ranked = sorted(en_likes.values(), reverse=True)
share = lambda k: sum(ranked[:k]) / t
indeg = Counter()
for l in open("data/graph/follows.tsv"):
    if "\t" in l and l.endswith("\n"):
        d, fs = l.rstrip("\n").split("\t")
        if d in english: indeg.update(x for x in fs.split(",") if x)
followed = [d for d, _ in indeg.most_common(1000)]
# Small accounts rarely appear in the sample, so many liked accounts have unknown language. Using only known accounts
# as the denominator would inflate these shares; divide by all English likes instead (English share from english-stats).
en_share = next(r["likes"] for r in json.load(open("data/english-stats.json"))["languages"] if r["code"] == "en")
denom = all_total * en_share
share = lambda k: sum(ranked[:k]) / denom
out = {"coverage": t / all_total, "accounts": len(en_likes), "top_by_likes": {str(k): share(k) for k in (100, 1000, 10000)},
       "top1000_by_follows": sum(en_likes.get(d, 0) for d in followed) / denom, "all_lang_top1000": sum(sorted(likes.values(), reverse=True)[:1000]) / all_total}
json.dump(out, open("data/top-accounts.json", "w"), indent=1); print(out)
