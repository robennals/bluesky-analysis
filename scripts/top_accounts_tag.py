"""Tag the most-liked accounts by what they post about, using Haiku.

Stage 1: fetch bio, follower count and recent original posts. Stage 2: propose a small category set from a random
subset. Stage 3: tag every account in batches. Tags describe posted content, never inferred personal traits.
Writes data/top-accounts-tags.json (resumable: finished batches are kept in data/top-tags-partial.jsonl).
"""
import glob, json, os, random, re, subprocess, sys, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "scripts")
from bsky import call

N = 1500; BATCH = 20
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
def haiku(prompt):
    for attempt in range(3):
        try:
            o = subprocess.run(["claude", "-p", "--model", "haiku", "--strict-mcp-config"], input=prompt, capture_output=True, text=True, timeout=240).stdout
            return json.loads(re.search(r"\{.*\}", o, re.S).group(0))
        except Exception as e:
            log("haiku retry", attempt, str(e)[:80])
    return None

likes, by_post = Counter(), Counter()
for f in glob.glob("data/engagement/eng-*.tsv"):
    for l in open(f):
        k, _, t = l.rstrip("\n").split("\t")
        if k == "like" and "/app.bsky.feed.post/" in t: likes[t.split("/")[2]] += 1; by_post[t] += 1
head = [d for d, _ in likes.most_common(N)]
arg = lambda k: next((a.split("=", 1)[1] for a in sys.argv if a.startswith(f"--{k}=")), None)
DIDS, PREFIX = arg("dids"), arg("prefix")   # tag any list of accounts, e.g. authors of a random sample of liked posts
if DIDS: head = json.load(open(DIDS))
TRIAL = "--trial" in sys.argv   # small run: 150 accounts for categories, 30 tagged, for a human to check before the full run
if TRIAL:
    random.seed(4); head = head[:10] + random.sample(head[10:], 140)

PATH = f"data/{PREFIX}-raw.json" if PREFIX else "data/top-accounts-trial-raw.json" if TRIAL else "data/top-accounts-raw.json"
if os.path.exists(PATH): raw = json.load(open(PATH))
else:
    prof = {}
    for i in range(0, len(head), 25):
        for p in call("app.bsky.actor.getProfiles", actors=head[i:i+25])["profiles"]: prof[p["did"]] = p
    # What earned the likes: each account's most-liked posts in the sample, including replies, plus its recent substantive posts.
    wanted = set(head); liked_posts = {}
    for u, n in by_post.most_common():
        d = u.split("/")[2]
        if d in wanted and len(liked_posts.setdefault(d, [])) < 6: liked_posts[d].append((u, n))
    uris = [u for v in liked_posts.values() for u, _ in v]; texts = {}
    def get(batch):
        try: return call("app.bsky.feed.getPosts", uris=batch)["posts"]
        except Exception: return []
    with ThreadPoolExecutor(3) as ex:
        for ps in ex.map(get, [uris[i:i+25] for i in range(0, len(uris), 25)]):
            for x in ps: texts[x["uri"]] = x
    def alts(x):
        e = x["record"].get("embed") or {}; m = e.get("media") or e
        return " ".join(f"[image: {i.get('alt')}]" for i in m.get("images") or [] if i.get("alt"))
    def quoted(x):
        e = x.get("embed") or {}; q = (e.get("record") or {}); q = q.get("record", q)
        t = (q.get("value") or {}).get("text") if isinstance(q, dict) else None
        return f" [QUOTING @{(q.get('author') or {}).get('handle', '?')}: {' '.join(t.split())[:150]}]" if t else ""
    body = lambda x: " ".join(((x["record"].get("text") or "") + " " + (((x.get("embed") or {}).get("external") or {}).get("title") or "") + " " + alts(x)).split()) + quoted(x)
    def feed(d):
        try: return d, call("app.bsky.feed.getAuthorFeed", actor=d, limit=40, filter="posts_with_replies")["feed"]
        except Exception: return d, []
    with ThreadPoolExecutor(3) as ex: all_items = dict(ex.map(feed, head))
    feeds = {d: [i["post"] for i in v if "reason" not in i] for d, v in all_items.items()}
    reposts = {d: [i["post"] for i in v if "reason" in i] for d, v in all_items.items()}
    raw = []
    for d in head:
        p = prof.get(d)
        if not p: continue
        ps = feeds.get(d, [])
        top = [(texts[u], n) for u, n in liked_posts.get(d, []) if u in texts]
        substantive = [body(x) for x in ps if len(body(x)) >= 60][:10]
        en = sum(((x["record"].get("langs") or [""])[0] or "").startswith("en") for x in ps)
        raw.append({"did": d, "handle": p["handle"], "name": p.get("displayName") or "", "bio": (p.get("description") or "")[:220], "followers": p.get("followersCount", 0),
                    "window_likes": likes[d], "liked_posts_seen": sum(1 for u in by_post if u.split("/")[2] == d) if TRIAL else None, "reply_share": sum(bool(x["record"].get("reply")) for x in ps) / max(1, len(ps)),
                    "en_share": en / max(1, len(ps)), "most_liked": [f"[{n} likes{' reply' if x['record'].get('reply') else ''}] {body(x)[:300]}" for x, n in top],
                    "posts": [t[:300] for t in dict.fromkeys(substantive)], "repost_share": len(reposts.get(d, [])) / max(1, len(all_items.get(d, []))),
                    "quote_share": sum(1 for x in ps if (x.get("embed") or {}).get("record")) / max(1, len(ps)),
                    "reposted": [f"[REPOST of @{x['author']['handle']}] {body(x)[:170]}" for x in reposts.get(d, [])[:8]]})
    json.dump(raw, open(PATH, "w"))
log("raw accounts", len(raw))

CATS = "data/top-accounts-categories.json"
view = lambda a: {"h": a["handle"], "name": a["name"], "bio": a["bio"], "followers": a["followers"], "most_liked_posts": a["most_liked"], "recent_substantive_posts": a["posts"], "reposts": a["reposted"]}
if os.path.exists(CATS): cats = json.load(open(CATS))
else:
    random.seed(2)
    cats = haiku("These are some of the most-liked accounts on Bluesky. Propose 10 to 14 categories that together cover what such accounts are mainly about, for a public analysis. "
                 "Categories describe what an account POSTS ABOUT or what it is (for example left-wing politics commentary, mainstream news organization, a politician, comedy, art, adult content, a specific recurring political cause), not personal traits. "
                 "Never use categories based on inferred religion, ethnicity, sexuality or health. Casual chat is not a topic: do not include a category for it. "
                 "Where a political cause recurs (for example Israel and Palestine), give it its own category. Include 'Other' and 'No clear topic' categories. "
                 "Return ONLY JSON {\"categories\": [{\"name\": \"2-4 plain words\", \"description\": \"one sentence\"}]}.\n\n" + json.dumps([view(a) for a in random.sample(raw, min(150, len(raw)))]))
    json.dump(cats, open(CATS, "w"), indent=1)
names = [c["name"] for c in cats["categories"]]
log("categories", names)

if TRIAL:
    PART = "data/top-tags-trial.jsonl"; raw = raw[:10] + random.sample(raw[10:], 50)
else:
    PART = f"data/{PREFIX}-tags-partial.jsonl" if PREFIX else "data/top-tags-partial.jsonl"
done = {json.loads(l)["handle"] for l in open(PART)} if os.path.exists(PART) else set()
todo = [a for a in raw if a["handle"] not in done]
def tag(batch):
    prompt = ("Tag each Bluesky account by the social clique it belongs to, as implied by what it says: for political accounts that means which side it is on, not just what subject it discusses. Any account that consistently takes one side belongs to that side's clique, even if it is a journalist, an outlet or an expert; 'Neutral news' is only for neutral reporting of what happened. Base sides only on stated positions, never on a person's presumed religion, ethnicity or nationality. Otherwise use the primary subject it discusses. Ignore casual chit-chat, greetings, thanks and short reactions: they are not topics. "
              "Weigh most_liked_posts most heavily, since they show what the account gets attention for. Judge the posts, not just the bio. Use 'No clear topic' only if nothing substantive is there. For US political accounts, choose the clique that best fits their tone and stance, not just the subject: a post can be about Trump and still be analytical, moderate or conservative. Use 'US independent wonk' only for accounts with no consistent left or right alignment, whose conclusions cut against both sides; a consistently left account goes in a US left category and a consistently right one in US conservative, however analytical its style.\n"
              "Many accounts mainly share other people's posts, so reposts and quoted posts are key evidence. A repost, or a short quote like 'This' or a pointing emoji, usually endorses the shared post: treat the shared content as the account's own topic. "
              "But a quote can attack or mock the original to invite criticism of it; then the account is against that content, so a quote mocking a MAGA post is anti-Trump, not conservative.\n"
              f"Allowed categories: {json.dumps(cats['categories'])}\n"
              "For each account return: category (exactly one allowed name), secondary (another allowed name or null), type (person, organization, parody, bot), "
              "lean (left, center, right, none: the politics of its posts), sharing (endorses: mainly amplifies content it agrees with; attacks: mainly quote-posts or reposts things in order to mock or criticize them, which is different from simply criticizing someone in its own words; both; or little), confidence (high, medium, low), and summary (under 12 words on what it posts). "
              "Describe content only; do not infer religion, ethnicity, sexuality or health.\n"
              "Return ONLY JSON {\"<handle>\": {\"category\": str, \"secondary\": str or null, \"type\": str, \"lean\": str, \"sharing\": str, \"confidence\": str, \"summary\": str}}.\n\n" + json.dumps([view(a) for a in batch]))
    r = haiku(prompt) or {}
    return [{"handle": a["handle"], **r[a["handle"]]} for a in batch if a["handle"] in r]
with ThreadPoolExecutor(4) as ex, open(PART, "a") as f:
    for i, rows in enumerate(ex.map(tag, [todo[i:i+BATCH] for i in range(0, len(todo), BATCH)])):
        for r in rows: f.write(json.dumps(r) + "\n")
        f.flush()
        if i % 10 == 0: log("batch", i)
tags = {r["handle"]: r for r in map(json.loads, open(PART))}
json.dump([{**a, **tags.get(a["handle"], {})} for a in raw], open(f"data/{PREFIX}-tags.json" if PREFIX else "data/top-accounts-trial-tags.json" if TRIAL else "data/top-accounts-tags.json", "w"))
log("tagged", len(tags), "of", len(raw))
c = Counter(tags[a["handle"]]["category"] for a in raw if a["handle"] in tags)
for k, v in c.most_common(): print(f"{v:5} {k}")
print(Counter(t["confidence"] for t in tags.values()), Counter(t["type"] for t in tags.values()))
