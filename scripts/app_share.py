"""How much atproto activity comes from apps other than Bluesky? Reads counts-*.json from jetstream-slots.mjs."""
import glob, json, sys
from collections import Counter

files = sorted(glob.glob(f"{sys.argv[1]}/counts-*.json"))
creates, writers, events = Counter(), Counter(), 0
for f in files:
    d = json.load(open(f)); events += d["events"]
    for k, v in d["counts"].items():
        if k.endswith(" create"): creates[k.rsplit(" ", 1)[0]] += v
    for k, v in d["writers"].items(): writers[k] += v   # summed over slots: account-slots, not unique accounts
def app(col):
    if col.startswith(("app.bsky.", "chat.bsky.")): return "Bluesky"
    parts = col.split(".")
    return ".".join(parts[:2]) if len(parts) > 2 else col
by_app, by_app_w = Counter(), Counter()
for k, v in creates.items(): by_app[app(k)] += v
for k, v in writers.items(): by_app_w[app(k)] = max(by_app_w[app(k)], v)
tot = sum(by_app.values())
print(f"{len(files)} slots, {events:,} events, {tot:,} record creates")
print(f"Bluesky {by_app['Bluesky']/tot:.2%} of creates; everything else {1-by_app['Bluesky']/tot:.2%}")
posts_like = sum(v for k, v in creates.items() if k in ("app.bsky.feed.post",))
print(f"\nNon-Bluesky apps by records created (and max distinct writers in any one 2-min slot):")
for a, v in by_app.most_common(40):
    if a != "Bluesky": print(f"  {v:7,}  {v/tot:.3%}  writers/slot<= {by_app_w[a]:4}  {a}")
nb = [a for a in by_app if a != "Bluesky"]
print(f"\n{len(nb)} distinct non-Bluesky namespaces seen. Bluesky posts alone: {posts_like:,}; all non-Bluesky records: {tot-by_app['Bluesky']:,}")
