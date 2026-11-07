"""Compare community assignments from two runs (e.g. 800 vs 2000 sampled users) on the core accounts they share.
Adjusted Rand index: 1 = identical groupings, 0 = no better than chance."""
import json, sys
from sklearn.metrics import adjusted_rand_score
a, b = (json.load(open(f))["labels"] for f in sys.argv[1:3])
shared = sorted(set(a) & set(b))
print(f"{len(shared)} shared core accounts (of {len(a)} / {len(b)}); ARI = {adjusted_rand_score([a[d] for d in shared], [b[d] for d in shared]):.2f}")
