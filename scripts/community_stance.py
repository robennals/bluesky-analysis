"""Stance of a community's members' political posts. Usage: community_stance.py <name prefix> [more prefixes...]"""
import json, random, re, subprocess, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
random.seed(9)
POL = re.compile(r"\b(trump|maga|republicans?|democrats?|gop|dems|biden|obama|vance|harris|ice|immigration|abortion|election|midterms?|congress|senate|liberals?|conservatives?|progressives?|tariffs?|israel|gaza|netanyahu|hamas|ukraine|russia|putin|zelensk\w*|nato|eu|brexit)\b", re.I)
d = json.load(open("data/viz-data.json")); mp = [json.loads(l) for l in open("data/graph/member-posts.jsonl")]
comm = json.load(open("data/graph/communities.json"))["membership"]
def stance(batch):
    prompt = ("Classify the political stance each post EXPRESSES. Labels: left (anti-Trump, pro-Democrat, progressive), right (pro-Trump, conservative, anti-left), "
              "center (explicitly moderate or criticizes both sides), pro-ukraine (supports Ukraine against Russia with no left/right signal), news (neutral reporting), unclear. "
              "Return ONLY a JSON array of labels, same length and order as the input.\n\n" + json.dumps([t[:240] for t in batch]))
    for _ in range(2):
        try:
            o = subprocess.run(["claude", "-p", "--model", "haiku", "--strict-mcp-config"], input=prompt, capture_output=True, text=True, timeout=200).stdout
            l = json.loads(re.search(r"\[.*\]", o, re.S).group(0))
            if len(l) == len(batch): return list(zip(batch, l))
        except Exception: pass
    return []
for prefix in sys.argv[1:]:
    c = next(x for x in d["communities"] if x["name"].startswith(prefix))
    users = {u for u, k in comm.items() if k == c["id"]}
    ps = [p["text"] for m in mp if m["did"] in users for p in m["posts"] if ((p.get("langs") or [""])[0] or "").startswith("en")]
    pol = [t for t in ps if POL.search(t or "") and len(t) > 40]
    s = random.sample(pol, min(200, len(pol)))
    with ThreadPoolExecutor(4) as ex: r = [x for b in ex.map(stance, [s[i:i+25] for i in range(0, len(s), 25)]) for x in b]
    n = Counter(l for _, l in r)
    print(f"\n{c['name']}: {len(users)} members; {len(ps)} English posts; {len(pol)} political ({len(pol)/max(1,len(ps)):.0%}); classified {len(r)}: {dict(n)}")
    print("core:", ", ".join("@" + a["handle"] for a in c["top"][:14]))
    for lab in ("right", "center"):
        for t, l in [x for x in r if x[1] == lab][:3]: print(f"  {lab}:", " ".join(t.split())[:140])
