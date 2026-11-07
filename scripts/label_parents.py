"""Name the top-level community groups with Haiku and aggregate their stats. Writes data/hierarchy-labels.json."""
import json, re, subprocess
from collections import Counter

d = json.load(open("data/viz-data.json")); h = json.load(open("data/graph/hierarchy.json"))
comms = {c["id"]: c for c in d["communities"]}
groups = {}
for c, p in h["parent_of"].items(): groups.setdefault(p, []).append(int(c))
def aggregate(id_, ids):
    ch = sorted((comms[i] for i in ids), key=lambda c: -c["members_in_sample"])
    posts = sum(c.get("posts_seen", 0) for c in ch) or 1
    mix = Counter()
    for c in ch:
        for k, v in c["category_mix"].items(): mix[k] += v * c.get("posts_seen", 0) / posts
    top = sorted((a for c in ch for a in c["top"]), key=lambda a: -a.get("indeg", 0))[:40]
    return {"id": id_, "children": [c["id"] for c in ch], "size": sum(c["size"] for c in ch),
            "members_in_sample": sum(c["members_in_sample"] for c in ch), "posts_seen": posts,
            "category_mix": dict(mix.most_common()), "top": top}
parents = sorted((aggregate(f"p{p}", ids) for p, ids in groups.items()), key=lambda p: -p["members_in_sample"])
umbrellas = []
for i, u in enumerate(h.get("umbrellas", [])):
    a = aggregate(f"u{i}", [c for g in u["groups"] for c in groups[g]])
    a.update(name=u["name"], groups=[f"p{g}" for g in u["groups"]],
             description="Communities whose accounts are followed mainly for left-leaning politics: grassroots activists and voters, Democratic politicians and legal commentators, liberal writers and journalists, and the British left.")
    umbrellas.append(a)
in_umbrella = {g for u in umbrellas for g in u["groups"]}
parents.sort(key=lambda p: (p["id"] not in in_umbrella, -p["members_in_sample"]))
prompt = ("Bluesky's follow graph has these top-level groups of communities, found by audience overlap. "
          "Give each group a plain, neutral name of 2-4 words that distinguishes it from the others, and a one-sentence description based on its communities. "
          "Return ONLY JSON {\"<id>\": {\"name\": str, \"description\": str}}.\n\n" +
          json.dumps([{"id": p["id"], "communities": [comms[c]["name"] for c in p["children"]],
                       "top_accounts": ["@" + a.get("handle", "") for a in p["top"][:15]],
                       "topics": list(p["category_mix"])[:4]} for p in parents]))
out = subprocess.run(["claude", "-p", "--model", "haiku", "--strict-mcp-config"], input=prompt, capture_output=True, text=True, timeout=300).stdout
names = json.loads(re.search(r"\{.*\}", out, re.S).group(0))
for p in parents: p.update(names[p["id"]])
json.dump({"parents": parents, "umbrellas": umbrellas}, open("data/hierarchy-labels.json", "w"), indent=1)
for p in parents: print(f'{p["name"]:36} members {p["members_in_sample"]:4} core {p["size"]:5} | {p["description"]}')
