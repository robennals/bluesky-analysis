"""Map who is on Bluesky: average each account's post embeddings, then cluster accounts into communities.

Averaging an account's posts washes out tone (jokes, replies, venting) and leaves what they post about.
Usage: .venv/bin/python scripts/cluster_accounts.py <slots_dir> <min_posts> <k> <out.md>
"""
import glob, json, os, re, sys
from collections import Counter, defaultdict
import numpy as np
from model2vec import StaticModel
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

slots, min_posts, k, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
URL = re.compile(r"https?://\S+|\b\S+\.(com|org|net|io|social|app|gg|co|uk|jp)/\S*")
posts = [json.loads(l) for f in sorted(glob.glob(f"{slots}/posts-*.jsonl")) for l in open(f)]
by = defaultdict(list)
seen = set()
for p in posts:
    if not ((p.get("langs") or [""])[0] or "").startswith("en"): continue
    t = " ".join(URL.sub(" ", p["text"] or "").split())
    if len(t) < 15 or t.lower() in seen: continue
    seen.add(t.lower()); by[p["did"]].append(t)
accts = [d for d, ts in by.items() if len(ts) >= min_posts]
print(f"{len(by)} English accounts; {len(accts)} with >= {min_posts} unique posts")
model = StaticModel.from_pretrained(os.path.join(os.path.dirname(__file__), "../data/models/potion-base-32M"))
vecs = []
for d in accts:
    E = model.encode(by[d], show_progress_bar=False)
    E = E[np.linalg.norm(E, axis=1) > 1e-6]
    v = E.mean(0) if len(E) else np.zeros(model.dim)
    vecs.append(v / (np.linalg.norm(v) + 1e-9))
X = np.array(vecs)
km = KMeans(n_clusters=k, random_state=0, n_init=5).fit(X)
docs = [" ".join(by[d]) for d in accts]
tf = TfidfVectorizer(stop_words="english", min_df=3, max_df=0.2, sublinear_tf=True, token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z']{2,}\b")
T = tf.fit_transform(docs); vocab = np.array(tf.get_feature_names_out())
cent = km.cluster_centers_ / np.linalg.norm(km.cluster_centers_, axis=1, keepdims=True)
rows = []
for c in range(k):
    idx = np.where(km.labels_ == c)[0]
    words = vocab[np.argsort(-np.asarray(T[idx].mean(0)).ravel())[:14]]
    sims = X[idx] @ cent[c]
    examples = [(accts[i], by[accts[i]][:3]) for i in idx[np.argsort(-sims)[:4]]]
    rows.append({"c": c, "n": len(idx), "share": len(idx) / len(accts), "posts": sum(len(by[accts[i]]) for i in idx),
                 "words": list(words), "examples": examples, "dids": [accts[i] for i in idx]})
rows.sort(key=lambda r: -r["n"])
json.dump(rows, open(out.replace(".md", ".json"), "w"), indent=1)
with open(out, "w") as f:
    f.write(f"# Bluesky account communities\n\n{len(accts):,} English accounts with >= {min_posts} posts in the sample, clustered into {k} groups by the average meaning of their posts.\n")
    for r in rows:
        f.write(f"\n## Group {r['c']}: {r['share']:.1%} of accounts ({r['n']} accounts, {r['posts']} posts)\n- words: {', '.join(r['words'])}\n")
        for d, ts in r["examples"][:3]:
            f.write(f"  - {' | '.join(t[:110] for t in ts)}\n")
print("wrote", out)
