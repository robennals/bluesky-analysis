"""Build pools of real examples for every selectable thing on the page. Writes data/sample-pools.json.

Every example is hydrated from the API (handle, like count, thumbnail). Images from posts carrying an adult label
are not embedded. Random pools are uniform; 'liked' pools are drawn in proportion to likes.
"""
import glob, json, os, random, re, sys, time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from model2vec import StaticModel
sys.path.insert(0, os.path.dirname(__file__))
from bsky import call
from hydrate import account_cards, add_reply_context, hydrate_posts
from post_format import fmt

random.seed(11)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
URL = re.compile(r"https?://\S+|\b\S+\.(com|org|net|io|social|app|gg|co|uk|jp)/\S*")
clean = lambda t: " ".join(URL.sub(" ", t or "").split())
is_en = lambda p: ((p.get("langs") or [""])[0] or "").startswith("en")
def take(xs, k): return random.sample(xs, min(k, len(xs)))
def weighted(xs, ws, k):
    if not xs: return []
    return list(dict.fromkeys(random.choices(xs, weights=ws, k=k * 3)))[:k]

posted = [json.loads(l) for f in sorted(glob.glob("data/slots/posts-*.jsonl")) for l in open(f)]
for p in posted: p["uri"] = f"at://{p['did']}/app.bsky.feed.post/{p['rkey']}"
liked = [json.loads(l) for l in open("data/engagement/liked-posts.jsonl")]
counts = {}
for l in open("data/graph/post-counts.tsv"):
    u, lk, *_ = l.rstrip("\n").split("\t"); counts[u] = int(lk)
cut = os.path.getmtime("data/graph/post-counts.tsv") - 12 * 3600
old = [p for p in posted if is_en(p) and p["uri"] in counts and time.mktime(time.strptime(p["t"][:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone < cut]
st = json.load(open("data/topics-stage1.json")); cent = np.array(st["centroids"]); cat_of = {c["id"]: c["category"] for c in st["clusters"]}
comm = json.load(open("data/graph/communities.json")); membership = comm["membership"]
model = StaticModel.from_pretrained("data/models/potion-base-32M")
def nearest(ps):
    ps = [p for p in ps if len(clean(p["text"])) >= 15]
    X = model.encode([clean(p["text"]) for p in ps], show_progress_bar=False)
    n = np.linalg.norm(X, axis=1); keep = n > 1e-6
    lab = ((X[keep] / n[keep, None]) @ cent.T).argmax(1)
    return [p for p, k in zip(ps, keep) if k], lab

# --- pools of URIs ---
pools = {"clusters": {}, "formats": {}, "like_buckets": {}, "like_tiers": {}, "communities": {}, "cells": {}, "languages": {}}
lang = lambda p: ((p.get("langs") or ["?"])[0] or "?").split("-")[0]
lp, ll = defaultdict(list), defaultdict(list)
for p in posted: lp[lang(p)].append(p["uri"])
for p in liked: ll[lang(p)].append(p)
for k in lp:
    pools["languages"][k] = {"posted": take(lp[k], 16), "liked": weighted([p["uri"] for p in ll[k]], [p["w"] for p in ll[k]], 16)}
Pe, lp = nearest([p for p in posted if is_en(p)]); Le, ll = nearest([p for p in liked if is_en(p)])
bp, bl = defaultdict(list), defaultdict(list)
for p, c in zip(Pe, lp): bp[int(c)].append(p["uri"])
for p, c in zip(Le, ll): bl[int(c)].append(p)
for c in range(len(cent)):
    pools["clusters"][str(c)] = {"posted": take(bp[c], 24), "liked": weighted([p["uri"] for p in bl[c]], [p["w"] for p in bl[c]], 24)}
fp = defaultdict(list)
for p in old: fp[fmt(p)].append(p["uri"])
for k, v in fp.items():
    nz = [u for u in v if counts[u] > 0]
    pools["formats"][k] = {"posted": take(v, 24), "liked": weighted(nz, [counts[u] for u in nz], 24)}
buckets = [("0", 0, 1), ("1", 1, 2), ("2–4", 2, 5), ("5–9", 5, 10), ("10–99", 10, 100), ("100–999", 100, 1000), ("1,000+", 1000, 10**9)]
for lab, a, b in buckets: pools["like_buckets"][lab] = take([p["uri"] for p in old if a <= counts[p["uri"]] < b], 24)
rank = sorted(old, key=lambda p: -counts[p["uri"]]); n = len(rank)
tiers = [("Top 0.1%", 0, n // 1000), ("Top 1%", n // 1000, n // 100), ("Top 10%", n // 100, n // 10), ("Bottom 90%", n // 10, n)]
for lab, a, b in tiers: pools["like_tiers"][lab] = take([p["uri"] for p in rank[a:b]], 24)
mp = [json.loads(l) for l in open("data/graph/member-posts.jsonl")]
mine = defaultdict(list); allm = []
for m in mp:
    c = membership.get(m["did"])
    if c is None: continue
    for p in m["posts"]:
        p = dict(p, comm=c); allm.append(p)
        if is_en(p): mine[c].append(p)
Me, lm = nearest([p for p in allm if is_en(p)])
cells = defaultdict(list)
for p, t in zip(Me, lm): cells[f'{p["comm"]}|{cat_of[int(t)]}'].append(p["uri"])
for k, v in cells.items(): pools["cells"][k] = take(v, 8)
def core_feed(a):
    try: return a["did"], [i["post"]["uri"] for i in call("app.bsky.feed.getAuthorFeed", actor=a["did"], limit=30, filter="posts_no_replies")["feed"] if "reason" not in i and is_en(i["post"]["record"])]
    except Exception: return a["did"], []
top = [(c["id"], a) for c in comm["communities"] for a in c["top"][:12]]
with ThreadPoolExecutor(3) as ex: cf = dict(ex.map(core_feed, [a for _, a in top]))
for c in comm["communities"]:
    ps = mine[c["id"]]; nz = [p for p in ps if p["likes"] > 0]
    core = [u for a in c["top"][:12] for u in take(cf.get(a["did"], []), 4)]
    pools["communities"][str(c["id"])] = {"core": take(core, 24), "members": take([p["uri"] for p in ps], 24),
                                          "popular": weighted([p["uri"] for p in nz], [p["likes"] for p in nz], 24)}
log("pools chosen")

# --- hydrate posts ---
def uris(o):
    if isinstance(o, str): yield o
    elif isinstance(o, list):
        for x in o: yield from uris(x)
    elif isinstance(o, dict):
        for x in o.values(): yield from uris(x)
allu = sorted(set(uris(pools)))
hyd = hydrate_posts(allu)
add_reply_context(hyd.values())
log("hydrated", len(hyd), "of", len(allu))
def fill(o):
    if isinstance(o, str): return hyd.get(o)
    if isinstance(o, list): return [y for y in (fill(x) for x in o) if y]
    return {k: fill(v) for k, v in o.items()}
pools = fill(pools)

# --- accounts ---
users, lists = [], []
for l in open("data/graph/follows.tsv"):
    if "\t" in l: u, fs = l.rstrip("\n").split("\t"); lists.append(fs.split(","))
indeg = Counter(x for fs in lists for x in fs if x); ranked = [d for d, _ in indeg.most_common()]
prof = {p["did"]: p for p in map(json.loads, open("data/graph/profiles.jsonl"))}
english = set(json.load(open("data/english-accounts.json")))
lists = [fs for u, fs in ((l.split("\t")[0], l.rstrip("\n").split("\t")[1].split(",")) for l in open("data/graph/follows.tsv") if "\t" in l) if u in english]
indeg = Counter(x for fs in lists for x in fs if x); ranked = [d for d, _ in indeg.most_common()]
acct = {"follow_tiers": {"Top 100": take(ranked[:100], 12), "Top 1,000": take(ranked[100:1000], 12), "Top 10,000": take(ranked[1000:10000], 12),
                         "Followed by 1 person": take([d for d in ranked if indeg[d] == 1], 12)}, "follower_buckets": {}}
fb = [("0", 0, 1), ("1–9", 1, 10), ("10–99", 10, 100), ("100–999", 100, 1000), ("1K–10K", 1000, 10000), ("10K–100K", 10000, 100000), ("100K+", 100000, 10**12)]
fc = [(p["did"], p.get("followersCount") or 0) for p in prof.values() if p["did"] in english]
for lab, a, b in fb: acct["follower_buckets"][lab] = take([d for d, n in fc if a <= n < b], 12)
if os.path.exists("data/graph/account-likes.jsonl"):
    rows = [r for r in map(json.loads, open("data/graph/account-likes.jsonl")) if "error" not in r and r["did"] in english]
    rows.sort(key=lambda r: -r["likes"]); n = len(rows)
    acct["account_buckets"] = {lab: take([r["did"] for r in rows if a <= r["likes"] < b], 12) for lab, a, b in
                               [("0", 0, 1), ("1–9", 1, 10), ("10–99", 10, 100), ("100–999", 100, 1000), ("1K–10K", 1000, 10000), ("10K+", 10000, 1e12)]}
    acct["account_tiers"] = {"Top 1%": take([r["did"] for r in rows[: n // 100]], 12), "Top 10%": take([r["did"] for r in rows[n // 100: n // 10]], 12),
                             "Middle": take([r["did"] for r in rows[n // 10: n // 2]], 12), "Bottom half": take([r["did"] for r in rows[n // 2:]], 12)}
cards = account_cards(d for g in acct.values() for v in g.values() for d in v)
accounts = {g: {k: [cards[d] for d in v if d in cards] for k, v in vals.items()} for g, vals in acct.items()}

# --- other apps ---
apps = {}
if os.path.exists("data/app-samples.json"):
    for app, recs in json.load(open("data/app-samples.json")).items():
        random.shuffle(recs); apps[app] = [{"c": r["collection"], "r": r["record"], "u": f"https://pdsls.dev/at://{r['did']}/{r['collection']}/{r['rkey']}"} for r in recs[:14]]
json.dump({"posts": pools, "accounts": accounts, "apps": apps}, open("data/sample-pools.json", "w"), separators=(",", ":"))
log("wrote sample-pools.json", os.path.getsize("data/sample-pools.json") // 1024, "KB")
