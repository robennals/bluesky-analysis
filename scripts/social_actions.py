"""Label what social action each randomly liked post is doing, using Haiku, and build the data for the page.

Reads the 1,000 random likes on English posts (data/like-sample.json) and the liked accounts' tags. Haiku sees the post
text, the thread it replies to, any quoted post or link, the post's image, and the author's account tag as context.
Resumable: finished batches are kept in data/social-actions-partial.jsonl. Writes data/social-actions.json.
Also reports agreement with the 80 hand labels from notes/2026-11-06-social-actions.md.
"""
import json, math, os, random, re, subprocess, sys, time, urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from hydrate import add_reply_context, hydrate_posts

BATCH = 10
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)

# The category tree from the hand-labelled pilot. Groups without sub-categories use the group key as their only leaf.
TREE = [
    ("us_vs_them", "Us vs them", "Takes a side in a political or cultural fight", [
        ("outgroup", "Against the outgroup", "Mocks, condemns or gloats over the other side, or exposes something outrageous it did. Includes political jokes at the other side's expense."),
        ("rally", "For the ingroup", "Rallies its own side: get out the vote, good polls, hope, pitching its policies."),
        ("police", "Policing the ingroup", "Attacks its own side, or people near it, for not being pure or loyal enough.")]),
    ("informing", "Informing and understanding", "Adds to what people know", [
        ("analysis", "Thoughtful analysis", "Works through an idea in a curious, fair way and admits limits. Includes constructive, good-faith criticism of its own side."),
        ("help", "Helping or teaching", "Non-political practical advice, how-tos, explanations, history or science facts, useful information."),
        ("news", "Plain news", "Reports what happened without much framing or taking a side.")]),
    ("making", "Making and appreciating", "Puts creative work or beauty in front of people", [
        ("own_work", "Own creative work", "The poster's own art, photos, comics, writing, music or crafts, including commissions and promotion of their work."),
        ("curating", "Curating others' work", "Shares someone else's art, photography or a cultural artefact for its beauty or interest.")]),
    ("belonging", "Belonging and connection", "Maintains a relationship or a shared identity", [
        ("fandom", "Fandom and community games", "Answering a prompt or hashtag game, excitement about a show, game, book or release, fan talk."),
        ("mourning", "Mourning or tribute", "Shared grief or tribute for someone who died."),
        ("personal", "Personal life sharing", "Life news and small moments from the poster's own life."),
        ("upkeep", "Community upkeep", "Thanks, greetings, congratulations, gifts, raffles, welcoming people.")]),
    ("entertaining", "Entertaining", "Non-political jokes, relatable observations, memes, cute animals", []),
    ("sexual", "Sexual display or flirting", "Nude or suggestive images, kink posts, flirting; includes sexual fan art", []),
    ("unclear", "Can't tell", "Not enough to tell what the post is doing", []),
]
LEAVES = {(sub or g): (g, sub or g) for g, _, _, subs in TREE for sub in ([s[0] for s in subs] or [None])}

# The pilot's hand labels, by position in data/social-action-sample.json.
MINE = {k: v for v, ks in {
    "outgroup": [2, 15, 27, 29, 31, 34, 38, 59, 69, 72], "rally": [14, 21, 65, 68, 70], "police": [10, 18, 20, 50], "analysis": [51],
    "help": [13, 45, 48, 52, 73], "news": [58], "own_work": [1, 11, 41, 62, 64, 66, 74, 75], "curating": [12, 37, 43],
    "fandom": [3, 8, 40, 78], "mourning": [19, 25, 28, 39, 71], "personal": [17, 53, 57, 76], "upkeep": [33, 47, 67],
    "entertaining": [0, 5, 9, 26, 30, 44, 46, 54, 77], "sexual": [4, 6, 7, 24, 32, 35, 36, 42, 49, 56, 79],
    "unclear": [16, 22, 23, 55, 60, 61, 63]}.items() for k in ks}


def haiku(prompt):
    for attempt in range(3):
        try:
            o = subprocess.run(["claude", "-p", "--model", "haiku", "--strict-mcp-config", "--allowedTools", "Read"], input=prompt, capture_output=True, text=True, timeout=400).stdout
            return json.loads(re.search(r"\{.*\}", o, re.S).group(0))
        except Exception as e:
            log("haiku retry", attempt, str(e)[:80])
    return None


def thumb(p, key):
    """Download a post's image preview so Haiku can look at it. Adult-labelled images are never downloaded; the label stands in."""
    if not p.get("i"): return None
    # Haiku's file reader decides what an image is by its extension, so name each file by its real format.
    have = [f for f in os.listdir("data/sa-thumbs") if f.split(".")[0] == key]
    if have: return os.path.abspath(f"data/sa-thumbs/{have[0]}")
    try: body = urllib.request.urlopen(p["i"], timeout=30).read()
    except Exception: return None
    ext = "webp" if body[8:12] == b"WEBP" else "png" if body[:4] == b"\x89PNG" else "jpg"
    path = os.path.abspath(f"data/sa-thumbs/{key}.{ext}"); open(path, "wb").write(body)
    return path


likes = json.load(open("data/like-sample.json"))
tags = {a["did"]: a for a in json.load(open("data/like-sample-tags.json"))}
top = set(json.load(open("data/top1000-dids.json")))
posts = hydrate_posts(l["uri"] for l in likes)
add_reply_context(posts.values())
os.makedirs("data/sa-thumbs", exist_ok=True)
items = [{"id": str(i), "uri": l["uri"], "did": l["did"], "post": posts[l["uri"]]} for i, l in enumerate(likes) if l["uri"] in posts]
with ThreadPoolExecutor(6) as ex: paths = list(ex.map(lambda it: thumb(it["post"], it["id"]), items))
for it, pth in zip(items, paths): it["img"] = pth
log("posts", len(items), "of", len(likes), "| with images", sum(bool(p) for p in paths))


def view(it):
    p, t = it["post"], tags.get(it["did"]) or {}
    v = {"id": it["id"], "author": "@" + p["h"], "text": p["t"]}
    if p.get("ctx"): v["replying_in_thread"] = [f"@{c['h']}: {c['t'][:200]}" for c in p["ctx"]]
    if p.get("q"): v["quoting"] = f"@{p.get('qh')}: {p['q']}"
    if p.get("x"): v["link_title"] = p["x"]
    if it["img"]: v["image_file"] = it["img"]
    elif p.get("a"): v["image"] = "an image the author or Bluesky labelled as adult content"
    if p.get("v"): v["video"] = True
    if t: v["author_context"] = f"{t.get('category', '')}: {t.get('summary', '')}"
    return v


GUIDE = "\n".join(f"- {name} ({desc})" + "".join(f"\n    - {k}: {n}. {d}" for k, n, d in subs) + ("" if subs else f" -> use key {g}") for g, name, desc, subs in TREE)
PROMPT = ("For each Bluesky post below, decide what social action the post itself is doing: what the poster is doing by posting it, and what it signals about them. "
          "Use the thread it replies to and any quoted post only to understand it. author_context describes the author's account in general; use it only when the post alone is ambiguous. "
          "If a post has an image_file, open it with the Read tool and look at it before deciding; many posts are mostly the image.\n"
          "Choose exactly one leaf key from this tree:\n" + GUIDE + "\n"
          "Context: these posts are from late October 2026. Actor Patrick Stewart had just died, so posts about him are usually tributes (mourning) even when joking. US midterm elections were a few days away.\n"
          "Own side means the broad coalition the poster belongs to: for a leftist, Democrats and liberals are part of their own side, so a leftist attacking Democrats for not going far enough is police, not outgroup.\n"
          "Rules: a joke at the political other side's expense is outgroup, not entertaining. Attacking one's own side for impurity is police; good-faith constructive criticism of one's own side is analysis. "
          "Sexual fan art is sexual, not own_work. Reporting a political event to alarm people about the other side is outgroup; neutral reporting is news. Use unclear only if you truly cannot tell.\n"
          "Return ONLY JSON {\"<id>\": {\"action\": \"<leaf key>\", \"confidence\": \"high|medium|low\", \"why\": \"under 12 words\"}}.\n\nPosts:\n")

PART = "data/social-actions-partial.jsonl"
done = {json.loads(l)["id"] for l in open(PART)} if os.path.exists(PART) else set()
todo = [it for it in items if it["id"] not in done]
LIMIT = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--limit=")), None)   # a small trial run before the full one
if LIMIT: todo = todo[:LIMIT]


def label(batch):
    r = haiku(PROMPT + json.dumps([view(it) for it in batch], ensure_ascii=False)) or {}
    return [{"id": it["id"], **r[it["id"]]} for it in batch if isinstance(r.get(it["id"]), dict) and r[it["id"]].get("action") in LEAVES]


with ThreadPoolExecutor(4) as ex, open(PART, "a") as f:
    for i, rows in enumerate(ex.map(label, [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)])):
        for r in rows: f.write(json.dumps(r) + "\n")
        f.flush()
        if i % 10 == 0: log("batch", i, "of", math.ceil(len(todo) / BATCH))
lab = {r["id"]: r for r in map(json.loads, open(PART))}
log("labelled", len(lab), "of", len(items))

# Shares overall, and split by whether the liked post's author is one of the 1,000 most-liked accounts.
labelled = [it for it in items if it["id"] in lab]
share = lambda xs, k: sum(lab[it["id"]]["action"] == k for it in xs) / max(1, len(xs))
tops, rest = [it for it in labelled if it["did"] in top], [it for it in labelled if it["did"] not in top]
random.seed(23); pool = defaultdict(list)
for it in labelled:
    pool[lab[it["id"]]["action"]].append({**it["post"], "why": lab[it["id"]]["why"], "conf": lab[it["id"]]["confidence"], "top": it["did"] in top})
moe = lambda p, n: 1.96 * math.sqrt(p * (1 - p) / max(1, n))
out = {"n": len(labelled), "n_top": len(tops), "n_rest": len(rest), "tree": [], "agreement": None}
for g, name, desc, subs in TREE:
    leaves = [s[0] for s in subs] or [g]
    node = {"key": g, "name": name, "desc": desc, "subs": []}
    for k in leaves:
        sub = next((s for s in subs if s[0] == k), (g, name, desc))
        node["subs"].append({"key": k, "name": sub[1], "desc": sub[2], "all": share(labelled, k), "top": share(tops, k), "rest": share(rest, k), "count": round(share(labelled, k) * len(labelled)),
                             "sample": random.sample(pool[k], min(40, len(pool[k])))})
    for f in ("all", "top", "rest"): node[f] = sum(s[f] for s in node["subs"])
    node["count"] = sum(s["count"] for s in node["subs"]); node["moe"] = moe(node["all"], len(labelled))
    out["tree"].append(node)

# Agreement with the hand labels on the pilot posts.
pilot = json.load(open("data/social-action-sample.json")); by_uri = {it["post"]["u"]: it["id"] for it in labelled}
pairs = [(MINE[i], lab[by_uri[p["u"]]]["action"]) for i, p in enumerate(pilot) if p["u"] in by_uri and by_uri[p["u"]] in lab]
grp = lambda k: LEAVES[k][0]
out["agreement"] = {"n": len(pairs), "leaf": sum(a == b for a, b in pairs) / max(1, len(pairs)), "group": sum(grp(a) == grp(b) for a, b in pairs) / max(1, len(pairs)),
                    "group_excluding_unclear": (lambda ps: sum(grp(a) == grp(b) for a, b in ps) / max(1, len(ps)))([(a, b) for a, b in pairs if a != "unclear"])}
json.dump(out, open("data/social-actions.json", "w"))
for n in out["tree"]:
    print(f'{n["all"]:6.1%} ±{n["moe"]:.1%}  top1000 {n["top"]:6.1%}  rest {n["rest"]:6.1%}  {n["name"]}')
    for s in n["subs"] if len(n["subs"]) > 1 else []: print(f'     {s["all"]:6.1%}  top1000 {s["top"]:6.1%}  rest {s["rest"]:6.1%}  {s["name"]}')
print("n", out["n"], "top", out["n_top"], "rest", out["n_rest"]); print("agreement with hand labels", out["agreement"])
print("disagreements:", Counter((a, b) for a, b in pairs if a != b).most_common(12))
