"""Follow-graph analysis from a random sample of active accounts' follow lists.

- How top-heavy is following? (share of follow edges going to the most-followed accounts; follower-count distribution)
- Who is core? (accounts followed by the most sampled active users)
- What are the communities? (core accounts clustered by who follows them), plus a 2D map.
- Which community does each sampled user belong to? (the one they follow most), and their recent posts.
Writes data/graph/communities.json, data/graph/member-posts.jsonl.
"""
import json, math, os, sys, time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from scipy import sparse
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.manifold import TSNE
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize
from bsky import call

G = os.path.join(os.path.dirname(__file__), "../data/graph")
arg = lambda name, default: int(next((a.split('=')[1] for a in sys.argv if a.startswith(f'--{name}=')), default))
CORE_N = arg('core', 2500)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)

# --- Load the sample of follow lists ---
users, lists = [], []
MAX_USERS = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--max-users=")), 10**9))
for l in open(f"{G}/follows.tsv"):
    if len(users) >= MAX_USERS or not l.endswith("\n") or "\t" not in l: break
    d, fs = l.rstrip("\n").split("\t")
    users.append(d); lists.append([x for x in fs.split(",") if x])
indeg = Counter(x for fs in lists for x in fs)
edges = sum(indeg.values())
ranked = [d for d, _ in indeg.most_common()]
def top_share(k): return sum(indeg[d] for d in ranked[:k]) / edges
stats = {"sample_users": len(users), "edges": edges, "distinct_targets": len(indeg),
         "median_follows": float(np.median([len(f) for f in lists])),
         "top_share": {k: top_share(k) for k in (10, 100, 1000, 10000)},
         "followed_by_1": sum(1 for v in indeg.values() if v == 1) / len(indeg)}
# Cumulative share curve: fraction of follow edges captured by the top x fraction of followed accounts.
xs = np.logspace(-5, 0, 60)
cum = np.cumsum([indeg[d] for d in ranked]) / edges
stats["edge_curve"] = [[float(x), float(cum[max(0, int(x * len(ranked)) - 1)])] for x in xs]
log("graph stats", json.dumps({k: v for k, v in stats.items() if k != "edge_curve"}))

# --- Follower-count distribution of active posters (from profiles of everyone who posted in the sample) ---
profs = [json.loads(l) for l in open(f"{G}/profiles.jsonl")]
fc = np.array([p.get("followersCount") or 0 for p in profs])
stats["followers_pct"] = {str(q): float(np.percentile(fc, q)) for q in (10, 25, 50, 75, 90, 99, 99.9)}
bins = [0, 1, 10, 100, 1000, 10000, 100000, 1e9]
stats["followers_hist"] = [[f"{int(bins[i])}–{int(bins[i+1]-1) if bins[i+1] < 1e9 else '+'}", int(((fc >= bins[i]) & (fc < bins[i+1])).sum())]
                           for i in range(len(bins) - 1)]
srt = np.sort(fc)[::-1]
stats["followers_top1pct_share"] = float(srt[: len(srt) // 100].sum() / srt.sum())

# --- Core accounts and their audience vectors ---
core = ranked[:CORE_N]
cidx = {d: i for i, d in enumerate(core)}
rows, cols = [], []
for u, fs in enumerate(lists):
    for x in fs:
        if x in cidx: rows.append(cidx[x]); cols.append(u)
M = sparse.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(core), len(users)))
# Down-weight users who follow a huge number of core accounts (follow-everyone accounts carry little signal).
ucount = np.asarray(M.sum(0)).ravel()
M = M.multiply(1 / np.log2(2 + ucount)).tocsr()
Z = normalize(TruncatedSVD(64, random_state=0).fit_transform(normalize(M)))
best = None
for k in ([arg('k', 0)] if arg('k', 0) else (12, 16, 20, 24)):
    km = KMeans(k, random_state=0, n_init=5).fit(Z)
    s = silhouette_score(Z, km.labels_, sample_size=2000, random_state=0)
    log("k", k, "silhouette", round(s, 3))
    if best is None or s > best[0]: best = (s, k, km)
_, K, km = best
xy = TSNE(2, random_state=0, init="pca", perplexity=40).fit_transform(Z)

# --- Profiles of core accounts ---
cp = {}
for i in range(0, len(core), 25):
    for p in call("app.bsky.actor.getProfiles", actors=core[i:i+25])["profiles"]:
        cp[p["did"]] = {"handle": p["handle"], "name": p.get("displayName") or "", "bio": (p.get("description") or "")[:200],
                        "followers": p.get("followersCount", 0)}
log("core profiles", len(cp))

# --- Assign sampled users to communities: the community they follow most (if they follow >= 5 core accounts) ---
lab = km.labels_
membership = {}
for u, fs in enumerate(lists):
    c = Counter(lab[cidx[x]] for x in fs if x in cidx)
    if sum(c.values()) >= 5: membership[users[u]] = int(c.most_common(1)[0][0])
log("users assigned", len(membership), "of", len(users))

communities = []
for c in range(K):
    idx = [i for i in range(len(core)) if lab[i] == c]
    idx.sort(key=lambda i: -indeg[core[i]])
    communities.append({"id": c, "size": len(idx), "members_in_sample": sum(1 for v in membership.values() if v == c),
                        "top": [{**cp.get(core[i], {"handle": core[i]}), "did": core[i], "indeg": indeg[core[i]]} for i in idx[:40]]})
points = [{"did": core[i], "handle": cp.get(core[i], {}).get("handle", ""), "name": cp.get(core[i], {}).get("name", ""),
           "c": int(lab[i]), "x": float(xy[i, 0]), "y": float(xy[i, 1]), "indeg": indeg[core[i]]} for i in range(len(core))]
json.dump({"stats": stats, "k": K, "communities": communities, "points": points, "membership": membership},
          open(f"{G}/communities.json", "w"))
json.dump({"n_users": len(users), "k": K, "labels": {core[i]: int(lab[i]) for i in range(len(core))}},
          open(f"{G}/labels-{len(users)}users.json", "w"))
log("wrote communities.json, K =", K)

# --- Recent posts of assigned members (to learn what each community talks about) ---
if "--no-feeds" in sys.argv: sys.exit(0)
done = set()
if os.path.exists(f"{G}/member-posts.jsonl"):
    done = {json.loads(l)["did"] for l in open(f"{G}/member-posts.jsonl")}
def feed(d):
    try: return d, call("app.bsky.feed.getAuthorFeed", actor=d, limit=40, filter="posts_no_replies")["feed"]
    except Exception: return d, []
with ThreadPoolExecutor(3) as ex, open(f"{G}/member-posts.jsonl", "a") as f:
    for n, (d, items) in enumerate(ex.map(feed, [d for d in membership if d not in done])):
        ps = [{"text": i["post"]["record"].get("text", ""), "langs": i["post"]["record"].get("langs"),
               "likes": i["post"].get("likeCount", 0), "uri": i["post"]["uri"]} for i in items if "reason" not in i]
        f.write(json.dumps({"did": d, "c": membership[d], "posts": ps}) + "\n")
        if n % 200 == 0: log("member feeds", n)
log("done")
