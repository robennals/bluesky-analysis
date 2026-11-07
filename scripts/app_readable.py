"""Turn raw records from non-Bluesky atproto apps into plain English, with Haiku. Writes data/app-readable.json."""
import json, random, re, subprocess
from concurrent.futures import ThreadPoolExecutor
random.seed(6)
SKIP = (".like", ".follow", ".repost", ".block", ".profile")
d = json.load(open("data/app-samples.json"))
def run(item):
    app, recs = item
    content = [r for r in recs if not r["collection"].endswith(SKIP)] or recs
    sample = random.sample(content, min(12, len(content)))
    prompt = ("These are raw data records written by one app on the AT Protocol, the open network Bluesky runs on. Some may be cut off.\n"
              "Return ONLY JSON {\"name\": \"the app's name as a reader would know it, or a plain guess\", \"about\": \"under 12 words on what the app does\", "
              "\"records\": [\"for each record, in order, one plain sentence saying what happened, e.g. 'Listened to Hello by Adele' or the post's actual text if it is a post\"]}. "
              "No ids, hashes or technical terms. If a record is encrypted or unintelligible, say 'Encrypted data' or 'Technical record'.\n\n"
              + json.dumps([{"type": r["collection"], "record": r["record"][:900]} for r in sample]))
    for _ in range(3):
        try:
            o = subprocess.run(["claude", "-p", "--model", "haiku", "--strict-mcp-config"], input=prompt, capture_output=True, text=True, timeout=200).stdout
            j = json.loads(re.search(r"\{.*\}", o, re.S).group(0))
            if len(j["records"]) == len(sample):
                return app, {"name": j["name"], "about": j["about"], "records": [{"t": t[:240], "c": r["collection"], "u": f"https://pdsls.dev/at://{r['did']}/{r['collection']}/{r['rkey']}"} for t, r in zip(j["records"], sample)]}
        except Exception: pass
    return app, None
with ThreadPoolExecutor(4) as ex: out = {k: v for k, v in ex.map(run, [(a, r) for a, r in d.items() if r]) if v}
json.dump(out, open("data/app-readable.json", "w"), ensure_ascii=False, indent=1)
for a, v in out.items(): print(f'{a:18} {v["name"][:24]:24} {v["about"][:60]:60} | {v["records"][0]["t"][:70]}')
print("missing:", [a for a, r in d.items() if a not in out])
