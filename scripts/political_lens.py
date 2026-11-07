"""Classify each community's political character with Haiku, from its top accounts, bio lines and members' posts.
Writes data/political-lens.json."""
import json, re, subprocess
d = json.load(open("data/viz-data.json"))
pools = json.load(open("data/sample-pools.json"))["posts"]["communities"]
desc = []
for c in d["communities"]:
    posts = pools.get(str(c["id"]), {})
    desc.append({"id": c["id"], "name": c["name"], "description": c["description"],
                 "top_accounts": [f"@{a.get('handle','')} {a.get('name','')}: {a.get('bio','')[:70]}" for a in c["top"][:15]],
                 "post_examples": [p["t"][:120] for p in (posts.get("core", [])[:5] + posts.get("members", [])[:5]) if p.get("t")],
                 "politics_share_of_member_posts": round(c["category_mix"].get("Politics, law and world news", 0), 2)})
prompt = ("Classify these Bluesky communities. For each return: lean (\"left\", \"center\", \"right\", or \"none\" if it isn't really political), "
          "political (true if politics is a main reason people follow these accounts, false if they are mainly followed for culture, entertainment or news), "
          "country (main country or \"international\"), and reason (under 15 words). Judge the accounts, not the community name. "
          "Return ONLY JSON {\"<id>\": {\"lean\": str, \"political\": bool, \"country\": str, \"reason\": str}}.\n\n" + json.dumps(desc))
out = subprocess.run(["claude", "-p", "--model", "haiku", "--strict-mcp-config"], input=prompt, capture_output=True, text=True, timeout=300).stdout
lens = json.loads(re.search(r"\{.*\}", out, re.S).group(0))
json.dump(lens, open("data/political-lens.json", "w"), indent=1)
for c in sorted(d["communities"], key=lambda c: -c["members_in_sample"]):
    l = lens[str(c["id"])]
    print(f'{c["name"][:42]:42} {c["members_in_sample"]:4} {l["lean"]:6} {str(l["political"]):5} {l["country"][:12]:12} {l["reason"]}')
