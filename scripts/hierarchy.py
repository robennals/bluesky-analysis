"""Find the hierarchy above the 20 follow-graph communities.

Rebuilds the audience embedding used by graph_analysis.py, takes each community's centroid, and clusters the
centroids bottom-up. Also tests how stable each top-level cut is on disjoint half-samples of users.
Writes data/graph/hierarchy.json.  Usage: hierarchy.py [n_parents]
"""
import json, random, sys
from collections import Counter
import numpy as np
from scipy import sparse
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import pdist
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import adjusted_rand_score as ari
from sklearn.preprocessing import normalize

CORE_N = 4000
comm = json.load(open("data/graph/communities.json"))
lab = {p["did"]: p["c"] for p in comm["points"]}
names = json.load(open("data/viz-data.json"))["communities"]
name = {c["id"]: c["name"] for c in names}
members = {c["id"]: c["members_in_sample"] for c in names}
K = comm["k"]
users, lists = [], []
for l in open("data/graph/follows.tsv"):
    if "\t" in l and l.endswith("\n"):
        d, fs = l.rstrip("\n").split("\t"); users.append(d); lists.append([x for x in fs.split(",") if x])
core = [p["did"] for p in comm["points"]]
cidx = {d: i for i, d in enumerate(core)}
def embed(ids):
    rows, cols = [], []
    for j, u in enumerate(ids):
        for x in lists[u]:
            if x in cidx: rows.append(cidx[x]); cols.append(j)
    M = sparse.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(core), len(ids)))
    M = M.multiply(1 / np.log2(2 + np.asarray(M.sum(0)).ravel())).tocsr()
    return normalize(TruncatedSVD(64, random_state=0).fit_transform(normalize(M)))
Z = embed(range(len(users)))
labels = np.array([lab[d] for d in core])
C = normalize(np.array([Z[labels == c].mean(0) for c in range(K)]))
L = linkage(C, "average", metric="cosine")
print("merge heights:", [round(float(h), 2) for h in L[:, 2]])
for n in (4, 5, 6, 7, 8):
    g = fcluster(L, n, "maxclust")
    print(f"\n--- {n} parents")
    for p in sorted(set(g)):
        ids = [c for c in range(K) if g[c] == p]
        print(f"  [{sum(members[c] for c in ids):4}] " + " | ".join(name[c] for c in sorted(ids, key=lambda c: -members[c])))
# Stability of a top-level split, independent of the 20: k-means at n on disjoint halves of users.
random.seed(0); idx = list(range(len(users))); random.shuffle(idx)
h1, h2 = embed(idx[: len(idx) // 2]), embed(idx[len(idx) // 2:])
for n in (4, 5, 6, 7, 8):
    print(f"k={n}: half-sample ARI {ari(KMeans(n, random_state=0, n_init=5).fit_predict(h1), KMeans(n, random_state=0, n_init=5).fit_predict(h2)):.2f}")
if len(sys.argv) > 1:
    n = int(sys.argv[1]); g = fcluster(L, n, "maxclust")
    json.dump({"n": n, "parent_of": {str(c): int(g[c]) for c in range(K)}, "linkage": L.tolist()}, open("data/graph/hierarchy.json", "w"))
