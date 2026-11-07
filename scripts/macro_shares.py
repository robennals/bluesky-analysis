"""Roll the 40 post clusters up into broad categories, and estimate the volume of long-form original posts.

The cluster -> category mapping below was assigned by hand from notes/clusters-raw.md (k=40, random_state=0).
"""
import glob, json, re
from collections import Counter

MACRO = {
  "Casual chat, banter, emotions": [34, 4, 3, 10, 2, 20, 25, 32, 18, 29, 9, 7, 6],
  "US politics & news": [30, 17, 8, 36, 26],
  "Adult content": [38, 33],
  "Bots, spam, automated feeds": [21, 24, 16, 15, 11, 23],
  "Entertainment & fandom (TV, film, games, streams)": [22, 0, 12, 27, 1],
  "Art & creators (compliments, sharing work)": [28, 31],
  "Hobbies & interests (music, sports, food, places)": [37, 14, 39, 19],
  "Tech, software, game dev": [13],
  "Non-English (pt/es, nl/de)": [5, 35],
}
d = json.load(open("notes/clusters-raw.json"))
share = {r["c"]: r["share"] for r in d["clusters"]}
assert sorted(c for cs in MACRO.values() for c in cs) == sorted(share), "every cluster must be mapped once"
print(f"Share of {d['unique_en']:,} unique English posts (>=25 chars):")
for name, cs in sorted(MACRO.items(), key=lambda kv: -sum(share[c] for c in kv[1])):
    print(f"  {sum(share[c] for c in cs):6.1%}  {name}")

# Long-form original posts: top-level, English, >= 250 chars of text after removing URLs and hashtags.
posts = [json.loads(l) for f in glob.glob("data/slots/posts-*.jsonl") for l in open(f)]
URL = re.compile(r"https?://\S+|#\S+")
en = [p for p in posts if ((p.get("langs") or [""])[0] or "").startswith("en")]
author = Counter(p["did"] for p in posts)
long = [p for p in en if not p["reply"] and len(" ".join(URL.sub(" ", p["text"] or "").split())) >= 250 and author[p["did"]] < 10]
print(f"\nLong original English posts (>=250 chars, top-level, not heavy posters): {len(long)} of {len(en)} English posts ({len(long)/len(en):.1%})")
print(f"  scaled to ~3.5M posts/day x {len(en)/len(posts):.0%} English: ~{3.5e6*len(en)/len(posts)*len(long)/len(en):,.0f} per day")
json.dump(long, open("data/slots/long-posts.json", "w"))
