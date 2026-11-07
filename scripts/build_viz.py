"""Inline data/viz-data.json into viz/template.html -> notes/bluesky-map.html (a single self-contained file)."""
import json, os
R = os.path.join(os.path.dirname(__file__), "..")
data = json.load(open(f"{R}/data/viz-data.json"))
for key, name in (("formats", "formats.json"), ("account_likes", "account-likes-summary.json"), ("hierarchy", "hierarchy-labels.json"), ("pools", "sample-pools.json"), ("flows", "group-flows.json"), ("top_accounts", "top-accounts.json"), ("attention", "attention.json"), ("cliques", "cliques.json"), ("like_cliques", "like-sample-cliques.json"), ("social_actions", "social-actions.json")):
    path = f"{R}/data/{name}"
    data[key] = json.load(open(path)) if os.path.exists(path) else None
data["scale"] = json.load(open(f"{R}/viz/scale.json"))
readable = json.load(open(f"{R}/data/app-readable.json"))
data["pools"]["apps"] = {k: v["records"] for k, v in readable.items()}
data["app_info"] = {k: {"name": v["name"], "about": v["about"]} for k, v in readable.items()}
es = json.load(open(f"{R}/data/english-stats.json"))
data["like_dist"] = es["like_dist"]; data["graph"] = {**data["graph"], **es["graph"]}; data["languages"] = es["languages"]; data["english_share_accounts"] = es["english_share_accounts"]
# Corrections to model-written names, where checking the content showed the name misled (see scripts/topic_mentions.py).
RENAME = {"Global news and Ukraine": ("Mainstream and international news", "Major newspapers, wire services and broadcasters, mostly US and UK, plus some European leaders and open-source investigators. They cover general news, including a lot of US politics.")}
for c in data["communities"] + (data.get("hierarchy") or {}).get("parents", []):
    for prefix, (nm, desc) in RENAME.items():
        if c.get("name", "").startswith(prefix): c.update(name=nm, description=desc)
# Posts tagged English that aren't: drop the topic clusters the labeller marked non-English and rescale what's left.
DROP = "Non-English posts"
kept = [c for c in data["clusters"] if c["category"] != DROP]
data["mislabelled_share"] = sum(c["vol"] for c in data["clusters"] if c["category"] == DROP)
vol, likes = sum(c["vol"] for c in kept), sum(c["likes"] for c in kept)
for c in kept: c["vol"] /= vol; c["likes"] /= likes
data["clusters"] = kept; data["categories"] = [c for c in data["categories"] if c["name"] != DROP]
def rescale(c):
    m = {k: v for k, v in c.get("category_mix", {}).items() if k != DROP}; t = sum(m.values()) or 1
    c["category_mix"] = {k: v / t for k, v in m.items()}
for group in (data["communities"], (data.get("hierarchy") or {}).get("parents", []), (data.get("hierarchy") or {}).get("umbrellas", [])):
    for c in group: rescale(c)
html = open(f"{R}/viz/template.html").read()
def for_page(page):
    """Each page carries only the data it shows, which keeps the files small enough to preview."""
    d = json.loads(json.dumps({**data, "page": page}))
    posts = d["pools"]["posts"]
    if page == "main":
        for k in ("clusters", "formats", "communities", "cells"): posts[k] = {}
        d["attention"]["pools"] = {}; d["points"] = []
    else:
        d["pools"]["posts"] = {k: posts[k] for k in ("clusters", "formats", "communities", "cells")}; d["pools"]["apps"] = {}
        for c in d["pools"]["posts"]["clusters"].values():   # keep the backup page small enough to preview
            for k in c: c[k] = c[k][:12]
        d["points"] = [{**p, "x": round(p["x"], 1), "y": round(p["y"], 1)} for p in d["points"]]
        for c in d["cliques"]["cliques"] + d["like_cliques"]["cliques"]: c["sample"] = []
        d["social_actions"] = None
    return d

# One template, two pages. Escape '</' so post text can never close the script tag.
for page, name in (("main", "bluesky-map.html"), ("topics", "bluesky-topics-backup.html")):
    blob = json.dumps(for_page(page), separators=(",", ":")).replace("</", "<\\/")
    open(f"{R}/notes/{name}", "w").write(html.replace("/*DATA*/null", blob))
    print(f"wrote notes/{name} ({os.path.getsize(f'{R}/notes/{name}')//1024} KB)")
