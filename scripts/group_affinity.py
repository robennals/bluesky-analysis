"""How do the top-level community groups relate? Centroid distances, and where each group's members actually point their follows."""
import json, sys
from collections import Counter, defaultdict
import numpy as np
from scipy.cluster.hierarchy import fcluster
sys.argv = sys.argv[:1]
exec(open("scripts/hierarchy.py").read().split("L = linkage(C")[0])   # reuse the embedding and centroids
L = np.array(json.load(open("data/graph/hierarchy.json"))["linkage"])
H = json.load(open("data/hierarchy-labels.json"))["parents"]
pname = {int(p["id"][1:]): p["name"] for p in H}
parent_of = {int(k): v for k, v in json.load(open("data/graph/hierarchy.json"))["parent_of"].items()}
for n in (2, 3, 4):
    g = fcluster(L, n, "maxclust"); print(f"\n{n} groups:")
    for x in sorted(set(g)):
        print("  ", " + ".join(sorted({pname[parent_of[c]] for c in range(K) if g[c] == x})))
ids = sorted(pname); PC = normalize(np.array([Z[np.isin(labels, [c for c in range(K) if parent_of[c] == p])].mean(0) for p in ids]))
print("\nCentroid similarity (cosine) between groups:")
sim = PC @ PC.T
for i, p in enumerate(ids):
    print(f"  {pname[p][:34]:34}", " ".join(f"{sim[i, j]:5.2f}" for j in range(len(ids))))
core_parent = {d: parent_of[lab[d]] for d in core}
member = comm["membership"]
foll = defaultdict(Counter)
for u, fs in zip(users, lists):
    if u in member:
        g = parent_of[member[u]]
        for x in fs:
            if x in core_parent: foll[g][core_parent[x]] += 1
print("\nWhere each group's members point their follows to core accounts (rows sum to 100%):")
print(" " * 36 + " ".join(f"{pname[p][:9]:>9}" for p in ids))
for p in ids:
    t = sum(foll[p].values()); print(f"  {pname[p][:34]:34}", " ".join(f"{foll[p][q] / t:9.0%}" for q in ids))
sizes = Counter(core_parent.values()); tot = sum(sizes.values())
print("Share of core accounts:      " + " " * 8 + " ".join(f"{sizes[q] / tot:9.0%}" for q in ids))
# Closest individual sub-communities to the gaming community
gid = next(c for c in range(K) if name[c].startswith("Gaming"))
print("\nClosest communities to gaming:", [(name[c], round(float(C[gid] @ C[c]), 2)) for c in np.argsort(-(C @ C[gid]))[1:6]])
order = [int(p["id"][1:]) for p in H]
json.dump({"groups": [f"p{p}" for p in order], "rows": [[foll[p][q] / sum(foll[p].values()) for q in order] for p in order],
           "core_share": [sizes[q] / tot for q in order]}, open("data/group-flows.json", "w"))
