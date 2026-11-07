"""Map what's on Bluesky: embed English posts, cluster them, and describe each cluster from data.

Usage: .venv/bin/python scripts/cluster_posts.py <slots_dir> <k> <out.md>
"""
import glob, json, os, re, sys
from collections import Counter
from urllib.parse import urlparse
import numpy as np
from model2vec import StaticModel
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import CountVectorizer

slots, k, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
posts = [json.loads(l) for f in sorted(glob.glob(f"{slots}/posts-*.jsonl")) for l in open(f)]
URL = re.compile(r"https?://\S+|\b\S+\.(com|org|net|io|social|app|gg|co|uk|jp)/\S*")
def clean(t): return " ".join(URL.sub(" ", t or "").split())
lang = Counter(((p.get("langs") or ["?"])[0] or "?").split("-")[0] for p in posts)
en = [p for p in posts if ((p.get("langs") or [""])[0] or "").startswith("en")]
for p in en: p["clean"] = clean(p["text"])
# Duplicate texts are almost always automated; count them before dropping.
dupe = Counter(p["clean"].lower() for p in en)
seen, docs = set(), []
for p in en:
    key = p["clean"].lower()
    if len(key) < 25 or key in seen: continue
    seen.add(key); docs.append(p)
author_n = Counter(p["did"] for p in posts)
print(f"{len(posts)} posts; {len(en)} English; {len(docs)} unique English with >=25 chars")

model = StaticModel.from_pretrained(os.path.join(os.path.dirname(__file__), "../data/models/potion-base-32M"))
X = model.encode([p["clean"] for p in docs], show_progress_bar=False)
norms = np.linalg.norm(X, axis=1)
keep = norms > 1e-6  # posts made only of tokens the model doesn't know embed to zero
docs = [d for d, ok in zip(docs, keep) if ok]
X = X[keep] / norms[keep, None]
km = MiniBatchKMeans(n_clusters=k, random_state=0, n_init=5, batch_size=4096).fit(X)
labels = km.labels_
cent = km.cluster_centers_ / np.linalg.norm(km.cluster_centers_, axis=1, keepdims=True)

# Distinctive words per cluster: frequency in cluster relative to overall (class-based TF-IDF).
cv = CountVectorizer(stop_words="english", min_df=5, max_df=0.3, token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z']{2,}\b")
W = cv.fit_transform([p["clean"] for p in docs])
vocab = np.array(cv.get_feature_names_out())
tot = np.asarray(W.sum(0)).ravel() + 1

rows = []
for c in range(k):
    idx = np.where(labels == c)[0]
    cw = np.asarray(W[idx].sum(0)).ravel()
    score = (cw / (cw.sum() + 1)) * np.log(1 + len(docs) / tot)
    words = vocab[np.argsort(-score)[:12]]
    sims = X[idx] @ cent[c]
    central = [docs[i] for i in idx[np.argsort(-sims)[:8]]]
    authors = Counter(docs[i]["did"] for i in idx)
    top10 = sum(n for _, n in authors.most_common(10)) / len(idx)
    heavy = sum(1 for i in idx if author_n[docs[i]["did"]] >= 20) / len(idx)
    doms = Counter(urlparse(docs[i]["ext"]).netloc.removeprefix("www.") for i in idx if docs[i].get("ext"))
    tags = Counter(t.lower() for i in idx for t in docs[i].get("tags", []))
    rows.append({"c": c, "n": len(idx), "share": len(idx) / len(docs), "words": list(words),
                 "reply": float(np.mean([docs[i]["reply"] for i in idx])), "authors": len(authors),
                 "top10_author_share": top10, "heavy_poster_share": heavy, "cohesion": float(sims.mean()),
                 "domains": doms.most_common(5), "tags": tags.most_common(6),
                 "central": [p["clean"][:200] for p in central]})
rows.sort(key=lambda r: -r["n"])
json.dump({"total": len(posts), "english": len(en), "unique_en": len(docs), "lang": lang.most_common(20),
           "dupe_share": 1 - len(set(dupe)) / len(en), "clusters": rows}, open(out.replace(".md", ".json"), "w"), indent=1)
with open(out, "w") as f:
    f.write(f"# Bluesky post clusters\n\n{len(posts):,} posts sampled; {len(en):,} English; {len(docs):,} unique English posts clustered into {k} groups.\n\n")
    f.write("Languages: " + ", ".join(f"{l} {n/len(posts):.0%}" for l, n in lang.most_common(10)) + "\n")
    for r in rows:
        f.write(f"\n## Cluster {r['c']}: {r['share']:.1%} ({r['n']} posts, {r['authors']} authors)\n")
        f.write(f"- words: {', '.join(r['words'])}\n- replies {r['reply']:.0%}; top-10 authors write {r['top10_author_share']:.0%}; "
                f"heavy posters {r['heavy_poster_share']:.0%}; cohesion {r['cohesion']:.2f}\n")
        if r["domains"]: f.write(f"- links: {', '.join(f'{d} {n}' for d, n in r['domains'])}\n")
        if r["tags"]: f.write(f"- tags: {', '.join(f'#{t} {n}' for t, n in r['tags'])}\n")
        for t in r["central"][:6]: f.write(f"  - {t}\n")
print("wrote", out)
