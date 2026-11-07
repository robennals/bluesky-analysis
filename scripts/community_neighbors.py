"""For one community (name prefix in argv[1]): nearest communities by audience, and where its members' follows go."""
import json, sys
from collections import Counter
import numpy as np
target = sys.argv[1]; sys.argv = sys.argv[:1]
exec(open("scripts/hierarchy.py").read().split("L = linkage(C")[0])
cid = next(c for c in range(K) if name[c].startswith(target))
print(name[cid], "| top:", ", ".join("@" + a["handle"] for a in next(c for c in names if c["id"] == cid)["top"][:12]))
print("nearest:", [(name[c], round(float(C[cid] @ C[c]), 2)) for c in np.argsort(-(C @ C[cid]))[1:7]])
member = comm["membership"]; f = Counter()
for u, fs in zip(users, lists):
    if member.get(u) == cid:
        for x in fs:
            if x in lab: f[lab[x]] += 1
tot = sum(f.values()); sz = Counter(labels.tolist())
print("members' follows (share | ratio to community's share of core):")
for c, v in f.most_common(7): print(f"  {name[c][:44]:44} {v / tot:5.1%}  {v / tot / (sz[c] / len(labels)):4.1f}x")
