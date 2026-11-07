"""Topics on Bluesky by volume (what's posted) and by likes (what's read), labelled by an LLM, crossed with
follow-graph communities. Writes data/viz-data.json for the visualization.

Inputs: data/slots/posts-*.jsonl (posted sample), data/engagement/liked-posts.jsonl (like-weighted sample),
data/graph/communities.json + member-posts.jsonl (communities and their members' posts), data/graph/post-counts.tsv.
"""
import glob, json, os, random, re, subprocess, sys, time
from collections import Counter, defaultdict
import numpy as np
from model2vec import StaticModel
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import CountVectorizer

ROOT = os.path.join(os.path.dirname(__file__), "..")
D = lambda *p: os.path.join(ROOT, "data", *p)
K = 60
random.seed(3)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
URL = re.compile(r"https?://\S+|\b\S+\.(com|org|net|io|social|app|gg|co|uk|jp)/\S*")
clean = lambda t: " ".join(URL.sub(" ", t or "").split())
is_en = lambda p: ((p.get("langs") or [""])[0] or "").startswith("en")
def post_url(uri):
    _, _, did, _, rkey = uri.split("/")
    return f"https://bsky.app/profile/{did}/post/{rkey}"

# --- Corpora ---
posted = [json.loads(l) for f in sorted(glob.glob(D("slots", "posts-*.jsonl"))) for l in open(f)]
for p in posted: p["uri"] = f"at://{p['did']}/app.bsky.feed.post/{p['rkey']}"
liked = [json.loads(l) for l in open(D("engagement", "liked-posts.jsonl"))]
lang_posted = Counter(((p.get("langs") or ["?"])[0] or "?").split("-")[0] for p in posted)
lang_liked = Counter()
for p in liked: lang_liked[((p.get("langs") or ["?"])[0] or "?").split("-")[0]] += p["w"]
P = [dict(p, clean=clean(p["text"]), src="posted", w=1) for p in posted if is_en(p)]
L = [dict(p, clean=clean(p["text"]), src="liked") for p in liked if is_en(p)]
# Liked posts with no text (images, videos) are a big share of what's liked: count them as their own bucket.
media_only_liked = sum(p["w"] for p in L if len(p["clean"]) < 15)
media_only_posted = sum(1 for p in P if len(p["clean"]) < 15)
P = [p for p in P if len(p["clean"]) >= 15]; L = [p for p in L if len(p["clean"]) >= 15]
log(f"posted EN {len(P)}; liked EN {len(L)} (weight {sum(p['w'] for p in L)})")

model = StaticModel.from_pretrained(D("models", "potion-base-32M"))
def embed(texts):
    X = model.encode(texts, show_progress_bar=False)
    n = np.linalg.norm(X, axis=1, keepdims=True)
    return np.where(n > 1e-6, X / np.maximum(n, 1e-6), 0)
XP, XL = embed([p["clean"] for p in P]), embed([p["clean"] for p in L])
okP, okL = np.abs(XP).sum(1) > 0, np.abs(XL).sum(1) > 0
P = [p for p, o in zip(P, okP) if o]; XP = XP[okP]
L = [p for p, o in zip(L, okL) if o]; XL = XL[okL]
def claude(prompt, model="haiku"):
    r = subprocess.run(["claude", "-p", "--model", model, "--strict-mcp-config", "--output-format", "text"],
                       input=prompt, capture_output=True, text=True, timeout=900)
    m = re.search(r"\{.*\}", r.stdout, re.S)
    if not m: sys.exit(f"LLM gave no JSON:\n{r.stdout[:2000]}\n{r.stderr[:2000]}")
    return json.loads(m.group(0))
STAGE1 = D("topics-stage1.json")
if os.path.exists(STAGE1):
    st = json.load(open(STAGE1)); clusters, labels = st["clusters"], st["labels"]
    cent = np.array(st["centroids"]); wL = sum(p["w"] for p in L)
    log("loaded cached topics")
else:
  X = np.vstack([XP, XL])
  km = KMeans(K, random_state=0, n_init=4).fit(X)
  cent = km.cluster_centers_ / np.linalg.norm(km.cluster_centers_, axis=1, keepdims=True)
  lp, ll = km.labels_[: len(P)], km.labels_[len(P):]
  docs = P + L
  cv = CountVectorizer(stop_words="english", min_df=5, max_df=0.3, token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z']{2,}\b")
  W = cv.fit_transform([p["clean"] for p in docs]); vocab = np.array(cv.get_feature_names_out())
  tot = np.asarray(W.sum(0)).ravel() + 1
  wP, wL = len(P), sum(p["w"] for p in L)
  clusters = []
  for c in range(K):
      ip, il = np.where(lp == c)[0], np.where(ll == c)[0]
      idx = np.concatenate([ip, il + len(P)])
      cw = np.asarray(W[idx].sum(0)).ravel()
      words = vocab[np.argsort(-(cw / (cw.sum() + 1)) * np.log(1 + len(docs) / tot))[:12]]
      authors = Counter(P[i]["did"] for i in ip)
      sp = [P[i] for i in random.sample(list(ip), min(8, len(ip)))]
      lw = [L[i] for i in il]
      sl = random.choices(lw, weights=[p["w"] for p in lw], k=min(8, len(lw))) if lw else []
      sl = list({p["uri"]: p for p in sl}.values())
      clusters.append({"id": c, "words": list(words), "vol": len(ip) / wP, "likes": sum(p["w"] for p in lw) / wL,
                       "top10_authors": sum(n for _, n in authors.most_common(10)) / max(1, len(ip)),
                       "samples_posted": [{"text": p["clean"][:280], "url": post_url(p["uri"]), "reply": p["reply"]} for p in sp],
                       "samples_liked": [{"text": p["clean"][:280], "url": post_url(p["uri"]), "likes": p.get("likeCount", 0)} for p in sl]})
  log("clustered")

  # --- LLM labelling (one call for all clusters) ---
  desc = [{"id": c["id"], "distinctive_words": c["words"],
           "examples": [s["text"][:160] for s in (c["samples_posted"][:5] + c["samples_liked"][:3])]} for c in clusters]
  labels = claude(
      "You are labelling clusters of Bluesky posts for a public analysis of what people do on Bluesky.\n"
      "Each cluster comes from k-means on text embeddings, so some clusters group posts by tone (casual replies, venting) rather than subject; label those honestly by what they are.\n"
      "Return ONLY JSON of the form {\"categories\": [{\"name\": str, \"description\": str}], "
      "\"clusters\": {\"<id>\": {\"label\": str, \"category\": str, \"description\": str}}}.\n"
      "Rules: 7–10 broad categories that together cover everything (e.g. politics, adult content, bots/spam, entertainment, conversation...). "
      "Every cluster gets exactly one category name from your list. Labels are 2–5 plain words. Descriptions are one plain sentence, neutral in tone.\n\n"
      + json.dumps(desc))
  for c in clusters:
      l = labels["clusters"].get(str(c["id"]), {})
      c.update(label=l.get("label", f"Cluster {c['id']}"), category=l.get("category", "Other"), description=l.get("description", ""))
  log("labelled", len(labels["categories"]), "categories")
  json.dump({"clusters": clusters, "labels": labels, "centroids": cent.tolist()}, open(STAGE1, "w"))

# --- Communities: topic mix of members' posts, and LLM names ---
if not os.path.exists(D("graph", "member-posts.jsonl")) or not os.path.exists(D("graph", "communities.json")):
    sys.exit("stage 1 done; communities not ready yet")
comm = json.load(open(D("graph", "communities.json")))
mix = defaultdict(Counter)
mposts = [json.loads(l) for l in open(D("graph", "member-posts.jsonl"))]
texts, owners = [], []
for m in mposts:
    c_now = comm["membership"].get(m["did"])  # current run's assignment; saved m["c"] may be from an older run
    if c_now is None: continue
    for p in m["posts"]:
        if is_en(p) and len(clean(p["text"])) >= 15: texts.append(clean(p["text"])); owners.append(c_now)
if texts:
    XM = embed(texts); ok = np.abs(XM).sum(1) > 0
    assign = (XM[ok] @ cent.T).argmax(1)
    for c_comm, c_topic in zip(np.array(owners)[ok], assign): mix[int(c_comm)][int(c_topic)] += 1
cat_of = {c["id"]: c["category"] for c in clusters}
for cm in comm["communities"]:
    m = mix[cm["id"]]; n = sum(m.values()) or 1
    cm["topic_mix"] = {str(t): v / n for t, v in m.most_common()}
    cats = Counter()
    for t, v in m.items(): cats[cat_of[t]] += v
    cm["category_mix"] = {k: v / n for k, v in cats.most_common()}
    cm["posts_seen"] = n
cdesc = [{"id": cm["id"], "core_accounts": [f"@{a.get('handle','')} — {a.get('name','')}: {a.get('bio','')[:90]}" for a in cm["top"][:25]],
          "top_member_topics": [next(c["label"] for c in clusters if c["id"] == int(t)) for t in list(cm["topic_mix"])[:5]]}
         for cm in comm["communities"]]
cl = claude(
    "These are communities found in Bluesky's follow graph: groups of widely-followed accounts that share an audience. "
    "For each, name the community in 2–5 plain words and give a one-sentence neutral description of who these accounts are and what their audience is into. "
    "Return ONLY JSON {\"<id>\": {\"name\": str, \"description\": str}}.\n\n" + json.dumps(cdesc))
for cm in comm["communities"]:
    l = cl.get(str(cm["id"]), {}); cm.update(name=l.get("name", f"Community {cm['id']}"), description=l.get("description", ""))
log("communities labelled")

# --- Post-level like distribution (posts at least 12h old when counted) ---
counts = {}
for l in open(D("graph", "post-counts.tsv")):
    u, lk, rp, rl, q = l.rstrip("\n").split("\t"); counts[u] = int(lk)
counted_at = os.path.getmtime(D("graph", "post-counts.tsv"))
old = [counts[p["uri"]] for p in posted if p["uri"] in counts and time.mktime(time.strptime(p["t"][:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone < counted_at - 12 * 3600]
old = np.sort(np.array(old))[::-1]; tl = old.sum()
like_dist = {"n_posts": int(len(old)), "total_likes": int(tl), "zero": float((old == 0).mean()), "median": float(np.median(old)),
             "mean": float(old.mean()), "top_share": {f: float(old[: max(1, int(len(old) * f))].sum() / tl) for f in (0.001, 0.01, 0.1)},
             "curve": [[float(x), float(old[: max(1, int(len(old) * x))].sum() / tl)] for x in np.logspace(-4, 0, 50)],
             "hist": [[lab, int(((old >= a) & (old < b)).sum())] for lab, a, b in
                      [("0", 0, 1), ("1", 1, 2), ("2–4", 2, 5), ("5–9", 5, 10), ("10–99", 10, 100), ("100–999", 100, 1000), ("1,000+", 1000, 10**9)]]}
log("like distribution", like_dist["top_share"], "zero", like_dist["zero"])

eng = Counter(l.split("\t", 1)[0] for f in glob.glob(D("engagement", "eng-*.tsv")) for l in open(f))
apps = json.load(open(D("app-share.json"))) if os.path.exists(D("app-share.json")) else None
json.dump({"generated": time.strftime("%Y-%m-%d %H:%M"), "categories": labels["categories"], "clusters": clusters,
           "media_only": {"posted_share": media_only_posted / (media_only_posted + len(P)), "liked_share": media_only_liked / (media_only_liked + wL)},
           "lang_posted": lang_posted.most_common(10), "lang_liked": lang_liked.most_common(10),
           "like_dist": like_dist, "graph": comm["stats"], "communities": comm["communities"], "points": comm["points"],
           "engagement_counts": eng, "apps": apps}, open(D("viz-data.json"), "w"))
log("wrote viz-data.json")
