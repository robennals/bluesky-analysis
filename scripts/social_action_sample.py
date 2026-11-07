"""Draw a small random set of liked posts, with reply context, to work out what social action each post is doing.
Writes data/social-action-sample.json and prints a compact listing to read."""
import json, random, sys
from hydrate import add_reply_context, hydrate_posts

N = int(sys.argv[1]) if len(sys.argv) > 1 else 80
likes = json.load(open("data/like-sample.json"))
random.seed(7); picked = random.sample(likes, min(N * 2, len(likes)))  # extra, since some posts are deleted
posts = hydrate_posts(l["uri"] for l in picked)
chosen = [posts[l["uri"]] for l in picked if l["uri"] in posts][:N]
add_reply_context(chosen)
json.dump(chosen, open("data/social-action-sample.json", "w"), indent=1)
for i, p in enumerate(chosen):
    extra = " ".join(f"[{k}: {p[k]}]" for k in ("x", "q") if p.get(k)) + (" [image]" if p.get("i") or p.get("a") else "") + (" [video]" if p.get("v") else "")
    print(f"\n#{i} @{p['h']} ({p['l']} likes)")
    for c in p.get("ctx", []): print(f"   ↳ replying in thread: @{c['h']}: {c['t'][:200]!r}")
    print(f"   {p['t']!r} {extra}")
