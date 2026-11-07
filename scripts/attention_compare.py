"""How do the accounts that get the attention differ from everyone else?

English accounts that posted during the sample are ranked by likes received across the sampled windows, then split into
the top 1%, next 9%, and other 90%. Writes data/attention.json with stats, topic and format mixes, and example pools.
"""
import glob, json, os, random, re, sys, time
from collections import Counter, defaultdict
import numpy as np
from model2vec import StaticModel
sys.path.insert(0, os.path.dirname(__file__))
from hydrate import account_cards, hydrate_posts
from post_format import fmt

random.seed(21)
GROUPS = ["Top 1%", "Next 9%", "Other 90%"]
DROP = "Non-English posts"
FMT = {"Video": "Video", "Images with text": "Images", "Images, no text": "Images", "Quote post with media": "Quote with media", "Quote post": "Quote post",
       "Link card": "Link", "Text with bare link": "Link", "GIF": "GIF"}
is_en = lambda p: ((p.get("langs") or [""])[0] or "").startswith("en")
URL = re.compile(r"https?://\S+|\b\S+\.(com|org|net|io|social|app|gg|co|uk|jp)/\S*")
clean = lambda t: " ".join(URL.sub(" ", t or "").split())

likes = Counter()
for f in glob.glob("data/engagement/eng-*.tsv"):
    for l in open(f):
        k, _, t = l.rstrip("\n").split("\t")
        if k == "like" and "/app.bsky.feed.post/" in t: likes[t.split("/")[2]] += 1
english = json.load(open("data/english-accounts.json"))
ranked = sorted(english, key=lambda d: (-likes[d], d)); n = len(ranked)
group = {d: GROUPS[0] if i < n // 100 else GROUPS[1] if i < n // 10 else GROUPS[2] for i, d in enumerate(ranked)}
prof = {p["did"]: p for p in map(json.loads, open("data/graph/profiles.jsonl"))}
posts = [p for f in glob.glob("data/slots/posts-*.jsonl") for p in map(json.loads, open(f)) if is_en(p) and p["did"] in group]
for p in posts: p["uri"] = f"at://{p['did']}/app.bsky.feed.post/{p['rkey']}"
st = json.load(open("data/topics-stage1.json")); cent = np.array(st["centroids"]); cat = {c["id"]: c["category"] for c in st["clusters"]}
model = StaticModel.from_pretrained("data/models/potion-base-32M")
tx = [p for p in posts if len(clean(p["text"])) >= 15]
X = model.encode([clean(p["text"]) for p in tx], show_progress_bar=False); nr = np.linalg.norm(X, axis=1); ok = nr > 1e-6
tx = [p for p, k in zip(tx, ok) if k]; lab = ((X[ok] / nr[ok, None]) @ cent.T).argmax(1)
for p, c in zip(tx, lab): p["cat"] = cat[int(c)]
for p in posts: p["fmt"] = FMT.get(fmt(p), "Text")

total = sum(likes[d] for d in english); out = {"n_accounts": n, "groups": GROUPS, "stats": {}, "topics": {}, "formats": {}}
TOP01 = "Top 0.1%"   # a subset of the top 1%, shown alongside it
top01 = set(ranked[: n // 1000])
members = lambda g: top01 if g == TOP01 else {d for d in ranked if group[d] == g}
for g in [TOP01] + GROUPS:
    ds_set = members(g); ds = [d for d in ranked if d in ds_set]; ps = [p for p in posts if p["did"] in ds_set]; ty = [p for p in ps if p.get("cat") and p["cat"] != DROP]
    ages = [(time.time() - time.mktime(time.strptime(prof[d]["createdAt"][:10], "%Y-%m-%d"))) / 86400 / 365.25 for d in ds if prof.get(d, {}).get("createdAt")]
    q = lambda k: float(np.median([prof[d].get(k) or 0 for d in ds if d in prof]))
    out["stats"][g] = {"accounts": len(ds), "like_share": sum(likes[d] for d in ds) / total, "post_share": len(ps) / len(posts), "median_followers": q("followersCount"), "median_follows": q("followsCount"),
                       "median_total_posts": q("postsCount"), "median_age_years": float(np.median(ages)), "reply_share": sum(p["reply"] for p in ps) / len(ps), "likes_per_account": sum(likes[d] for d in ds) / len(ds)}
    c = Counter(p["cat"] for p in ty); out["topics"][g] = {k: v / len(ty) for k, v in c.items()}
    c = Counter(p["fmt"] for p in ps); out["formats"][g] = {k: v / len(ps) for k, v in c.items()}
# example pools: by group overall, by group x topic, by group x format
pool = defaultdict(list)
for p in posts:
    g = group[p["did"]]; pool[("all", g)].append(p["uri"]); pool[("fmt", g, p["fmt"])].append(p["uri"])
    if p.get("cat") and p["cat"] != DROP: pool[("cat", g, p["cat"])].append(p["uri"])
top_like = lambda u: 1
chosen = {k: random.sample(v, min(24 if k[0] == "all" else 12, len(v))) for k, v in pool.items()}
hyd = hydrate_posts(u for v in chosen.values() for u in v)
accts = {g: random.sample(sorted(members(g)), min(20, len(members(g)))) for g in [TOP01] + GROUPS}
cards = account_cards(d for v in accts.values() for d in v)
out["pools"] = {"|".join(k): [hyd[u] for u in v if u in hyd] for k, v in chosen.items()}
out["accounts"] = {g: [cards[d] for d in v if d in cards] for g, v in accts.items()}
json.dump(out, open("data/attention.json", "w"), separators=(",", ":"))
for g in [TOP01] + GROUPS: print(g, json.dumps({k: round(v, 3) for k, v in out["stats"][g].items()}))
print("topics", {g: {k: round(v, 3) for k, v in sorted(out["topics"][g].items(), key=lambda x: -x[1])} for g in (GROUPS[0], GROUPS[2])})
print("formats", {g: {k: round(v, 3) for k, v in sorted(out["formats"][g].items(), key=lambda x: -x[1])} for g in (GROUPS[0], GROUPS[2])})
