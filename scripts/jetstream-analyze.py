"""Summarize a Jetstream sample: record types, other atproto apps, languages, links, hashtags, heavy posters."""
import json, re, sys, random
from collections import Counter
from urllib.parse import urlparse

d = sys.argv[1] if len(sys.argv) > 1 else "../data/jetstream"
c = json.load(open(f"{d}/counts.json"))
posts = [json.loads(l) for l in open(f"{d}/posts.jsonl")]
mins = c["minutes"]
print(f"## {c['events']:,} events in {mins} min ({c['events']/mins/60:.0f}/s); {len(posts):,} posts ({len(posts)/mins/60:.1f}/s)")

print("\n## Record types (creates), per minute")
creates = Counter({k.rsplit(' ', 1)[0]: v for k, v in c["counts"].items() if k.endswith(" create")})
for k, v in creates.most_common(25): print(f"  {v/mins:9.0f}/min  {k}")
print("\n## Non-Bluesky apps (collections not under app.bsky / chat.bsky)")
other = Counter()
for k, v in creates.items():
    if not k.startswith(("app.bsky.", "chat.bsky.")): other[".".join(k.split(".")[:2]) if k.count(".") > 2 else k] += v
for k, v in other.most_common(30): print(f"  {v:7}  {k}")
print("  distinct accounts writing non-Bluesky records:",
      sum(1 for did, cols in c["perDid"].items() if any(not x.startswith(("app.bsky.", "chat.bsky.")) for x in cols)))

print("\n## Posts")
top = [p for p in posts if not p["reply"]]
print(f"  replies {1-len(top)/len(posts):.0%}; with images {sum(p.get('embed') in ('app.bsky.embed.images','app.bsky.embed.recordWithMedia') for p in posts)/len(posts):.0%};"
      f" video {sum(p.get('embed')=='app.bsky.embed.video' for p in posts)/len(posts):.0%}; links {sum(bool(p.get('ext') or p['links']) for p in posts)/len(posts):.0%};"
      f" quotes {sum(bool(p.get('quote')) for p in posts)/len(posts):.0%}; empty text {sum(not p['text'].strip() for p in posts)/len(posts):.0%}")
langs = Counter((p.get("langs") or ["?"])[0].split("-")[0] for p in posts)
print("  languages:", ", ".join(f"{k} {v/len(posts):.0%}" for k, v in langs.most_common(12)))
doms = Counter()
for p in posts:
    for u in ([p["ext"]] if p.get("ext") else []) + p["links"]:
        h = urlparse(u).netloc.lower().removeprefix("www.")
        if h: doms[h] += 1
print("  top link domains:", ", ".join(f"{k} {v}" for k, v in doms.most_common(30)))
tags = Counter(t.lower() for p in posts for t in p["tags"])
print("  top hashtags:", ", ".join(f"#{k} {v}" for k, v in tags.most_common(40)))

print("\n## Who posts")
by = Counter(p["did"] for p in posts)
n = len(by); heavy = [d for d, k in by.items() if k >= 15]
print(f"  {n:,} distinct posters; top 1% wrote {sum(k for _, k in by.most_common(max(1, n//100)))/len(posts):.0%} of posts;"
      f" {len(heavy)} accounts posted >=15 times in {mins} min ({sum(by[d] for d in heavy)/len(posts):.0%} of posts)")
json.dump([{"did": d, "n": k} for d, k in by.most_common(60)], open(f"{d}/heavy.json", "w"))

ai = re.compile(r"\b(AI|LLM|ChatGPT|Claude|Gemini|OpenAI|Anthropic|AI agents?|chatbots?)\b")
print(f"\n## AI mentioned in {sum(bool(ai.search(p['text'])) for p in posts)/len(posts):.1%} of posts;"
      f" 'agent' {sum(bool(re.search(r'\\bagents?\\b', p['text'], re.I)) for p in posts)/len(posts):.1%}")
random.seed(1)
en = [p for p in top if (p.get("langs") or [""])[0].startswith("en") and len(p["text"]) > 40 and by[p["did"]] < 15]
json.dump(random.sample(en, min(500, len(en))), open(f"{d}/sample-en.json", "w"), indent=0)
