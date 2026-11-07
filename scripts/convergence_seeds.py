"""Is community instability due to sample size or to k-means itself? Rebuild the same audience embedding as
graph_analysis.py, then compare k-means runs with different seeds (same data) and on half-samples (different data)."""
import random, sys
from collections import Counter
import numpy as np
from scipy import sparse
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import adjusted_rand_score as ari
from sklearn.preprocessing import normalize

CORE_N, K = 4000, 20
users, lists = [], []
for l in open("data/graph/follows.tsv"):
    if "\t" in l and l.endswith("\n"):
        d, fs = l.rstrip("\n").split("\t"); users.append(d); lists.append([x for x in fs.split(",") if x])
core = [d for d, _ in Counter(x for fs in lists for x in fs).most_common(CORE_N)]
cidx = {d: i for i, d in enumerate(core)}
def embed(user_ids):
    rows, cols = [], []
    for j, u in enumerate(user_ids):
        for x in lists[u]:
            if x in cidx: rows.append(cidx[x]); cols.append(j)
    M = sparse.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(core), len(user_ids)))
    M = M.multiply(1 / np.log2(2 + np.asarray(M.sum(0)).ravel())).tocsr()
    return normalize(TruncatedSVD(64, random_state=0).fit_transform(normalize(M)))
Z = embed(range(len(users)))
runs = [KMeans(K, random_state=s, n_init=5).fit_predict(Z) for s in range(3)]
print("same data, different seeds: ARI", [round(ari(runs[i], runs[j]), 2) for i, j in ((0, 1), (0, 2), (1, 2))])
random.seed(0); idx = list(range(len(users))); random.shuffle(idx)
h1, h2 = embed(idx[: len(idx) // 2]), embed(idx[len(idx) // 2:])
a, b = KMeans(K, random_state=0, n_init=5).fit_predict(h1), KMeans(K, random_state=0, n_init=5).fit_predict(h2)
print("disjoint half-samples (~994 users each): ARI", round(ari(a, b), 2))
for k in (6, 10):
    r = [KMeans(k, random_state=s, n_init=5).fit_predict(Z) for s in range(2)]
    a, b = KMeans(k, random_state=0, n_init=5).fit_predict(h1), KMeans(k, random_state=0, n_init=5).fit_predict(h2)
    print(f"k={k}: seeds ARI {ari(*r):.2f}; half-samples ARI {ari(a, b):.2f}")
