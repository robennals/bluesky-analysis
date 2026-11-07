"""Second pass on the anti-Trump and moderate tags: separate the left from non-left anti-Trump voices and true moderates."""
import json, re, subprocess
from concurrent.futures import ThreadPoolExecutor
NT, MOD, LEFT = "Anti-Trump, not left", "US moderate or centrist", "US left: anti-Trump partisan"
import sys
p = sys.argv[1] if len(sys.argv) > 1 else "data/top-accounts-tags.json"; rows = json.load(open(p))
todo = [a for a in rows if a.get("category") in (MOD, LEFT)]
print(len(todo), "to check")
def check(batch):
    prompt = ("These Bluesky accounts oppose Trump or were tagged moderate. Decide which group each belongs to, judging from its bio and what it says and shares:\n"
              f"'{LEFT}': Democratic-aligned or left-leaning voices whose main theme is opposing Trump and Republicans.\n"
              f"'{NT}': anti-Trump voices who are not on the left, such as Never-Trump conservatives, former Republicans, and centre-right commentators, whose main theme is opposing Trump.\n"
              f"'{MOD}': true moderates or centrists whose main theme is moderation itself or criticizing both sides, not mainly opposing Trump.\n"
              "Return ONLY JSON {\"<handle>\": \"<group name>\"}.\n\n" +
              json.dumps([{"h": a["handle"], "name": a["name"], "bio": a["bio"], "posts": (a["most_liked"] + a["posts"])[:8]} for a in batch]))
    for _ in range(3):
        try:
            o = subprocess.run(["claude", "-p", "--model", "haiku", "--strict-mcp-config"], input=prompt, capture_output=True, text=True, timeout=240).stdout
            return json.loads(re.search(r"\{.*\}", o, re.S).group(0))
        except Exception: pass
    return {}
res = {}
with ThreadPoolExecutor(4) as ex:
    for r in ex.map(check, [todo[i:i+20] for i in range(0, len(todo), 20)]): res.update(r)
for a in rows:
    if a["handle"] in res and res[a["handle"]] in (NT, MOD, LEFT): a["category"] = res[a["handle"]]
json.dump(rows, open(p, "w"))
c = json.load(open("data/top-accounts-categories.json"))
if not any(x["name"] == NT for x in c["categories"]):
    i = [x["name"] for x in c["categories"]].index(MOD)
    c["categories"].insert(i, {"name": NT, "description": "Anti-Trump voices who are not on the left: Never-Trump conservatives and former Republicans."})
    json.dump(c, open("data/top-accounts-categories.json", "w"), indent=1)
for k in (NT, MOD):
    print("\n" + k); [print(f'  {a["followers"]:>8} @{a["handle"][:32]:32} {a["summary"][:70]}') for a in sorted(rows, key=lambda a: -a["followers"]) if a.get("category") == k]
print("left now", sum(a.get("category") == LEFT for a in rows))
