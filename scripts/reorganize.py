"""Rebuild the hierarchy with a 'Left politics' umbrella: communities the political lens marks as left and political go
under it, keeping their audience-based group; left commentary from other groups forms its own groups."""
import json
h = json.load(open("data/graph/hierarchy.json")); lens = json.load(open("data/political-lens.json"))
labels = json.load(open("data/hierarchy-labels.json"))["parents"]
if "audience_parent_of" not in h: h["audience_parent_of"] = h["parent_of"]
aud = {int(k): v for k, v in h["audience_parent_of"].items()}
oldname = {int(p["id"][1:]): p["name"] for p in labels}
if "audience_names" not in h: h["audience_names"] = {str(k): v for k, v in oldname.items()}
oldname = {int(k): v for k, v in h["audience_names"].items()}
is_left = lambda c: lens[str(c)]["lean"] == "left" and lens[str(c)]["political"]
new, left_groups = {}, set()
for c, p in aud.items():
    nm = oldname[p]
    if is_left(c):
        g = p if nm.startswith(("Grassroots", "National")) else (100 if nm.startswith("Celebrities") else 101)
        left_groups.add(g)
    else: g = p
    new[c] = g
h["parent_of"] = {str(k): v for k, v in new.items()}; h["umbrellas"] = [{"name": "Left politics", "groups": sorted(left_groups)}]
json.dump(h, open("data/graph/hierarchy.json", "w"))
print("groups:", sorted(set(new.values())), "left:", sorted(left_groups))
