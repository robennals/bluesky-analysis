"""How often do each community's core accounts and members mention given terms? Checks community names against content."""
import json, re, sys
from collections import Counter
from bsky import call
is_en = lambda r: ((r.get("langs") or [""])[0] or "").startswith("en")
T = re.compile(r"\btrump|\bmaga\b|white house|\bgop\b|republican|democrat|\bdoj\b|\bice\b", re.I); U = re.compile(r"ukrain|russia|putin|zelensk|kyiv|kremlin", re.I); W = re.compile(r"\b(iran|israel|gaza|china|brazil|lula|europe|\beu\b|canada|india|africa|nato|bolsonaro|venezuela|france|germany|korea|japan)\b", re.I)
d = json.load(open("../data/viz-data.json")); comm = json.load(open("../data/graph/communities.json"))["membership"]
mem = {}
for l in open("../data/graph/member-posts.jsonl"):
    m = json.loads(l); c = comm.get(m["did"])
    if c is not None: mem.setdefault(c, []).extend(p["text"] for p in m["posts"] if is_en(p))
def core(c):
    out = []
    for a in c["top"][:12]:
        try: out += [(i["post"]["record"].get("text", "") + " " + (((i["post"].get("embed") or {}).get("external") or {}).get("title") or "")) for i in call("app.bsky.feed.getAuthorFeed", actor=a["did"], limit=30, filter="posts_no_replies")["feed"] if "reason" not in i and is_en(i["post"]["record"])]
        except Exception: pass
    return out
rate = lambda xs, rx: sum(bool(rx.search(t or "")) for t in xs) / max(1, len(xs))
print(f"{'community':44} {'core n':>6} T%  U%  World% | {'memb n':>6} T%  U%  World%")
for c in sorted(d["communities"], key=lambda c: -c["members_in_sample"]):
    k = core(c); m = mem.get(c["id"], [])
    if len(m) < 100: continue
    print(f"{c['name'][:44]:44} {len(k):6} {rate(k,T):3.0%} {rate(k,U):3.0%} {rate(k,W):4.0%}  | {len(m):6} {rate(m,T):3.0%} {rate(m,U):3.0%} {rate(m,W):4.0%}")
g = next(c for c in d["communities"] if c["name"].startswith("Global"))
print("\nGlobal news core:", ", ".join(f"@{a['handle']}" for a in g["top"][:25]))
lens = json.load(open("../data/political-lens.json"))
