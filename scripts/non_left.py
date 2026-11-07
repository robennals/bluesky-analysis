"""Is there non-left activity at scale? (1) LLM stance of random political posts, by volume and by likes;
(2) how many sampled active users follow known centrist/right accounts; (3) self-described accounts by bio."""
import glob, json, random, re, subprocess, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "scripts")
from bsky import call, paginate
random.seed(5)
POL = re.compile(r"\b(trump|maga|republicans?|democrats?|gop|dems|biden|obama|vance|harris|newsom|ice|immigration|abortion|election|midterms?|congress|senate|liberals?|conservatives?|progressives?|woke|tariffs?|border|israel|gaza|netanyahu|hamas)\b", re.I)
is_en = lambda p: ((p.get("langs") or [""])[0] or "").startswith("en")
posted = [json.loads(l) for f in glob.glob("data/slots/posts-*.jsonl") for l in open(f)]
liked = [json.loads(l) for l in open("data/engagement/liked-posts.jsonl")]
A = [p for p in posted if is_en(p) and POL.search(p["text"] or "") and len(p["text"]) > 40]
B = [p for p in liked if is_en(p) and POL.search(p["text"] or "") and len(p["text"]) > 40]
print(f"political-keyword posts: {len(A)} of {sum(map(is_en, posted))} English posted; liked: {sum(p['w'] for p in B)} of {sum(p['w'] for p in liked if is_en(p))} likes")
sa = random.sample(A, 600); sb = random.choices(B, weights=[p["w"] for p in B], k=600)
def stance(batch):
    prompt = ("Classify the political stance each Bluesky post EXPRESSES. Labels: left (anti-Trump, pro-Democrat, progressive), right (pro-Trump, pro-Republican, conservative, anti-left), "
              "center (explicitly moderate, or criticizes both sides), news (neutral reporting), unclear (not political or can't tell, including sarcasm you can't resolve). "
              "Return ONLY a JSON array of labels, in order, same length as the input.\n\n" + json.dumps([p["text"][:280] for p in batch]))
    try:
        o = subprocess.run(["claude", "-p", "--model", "haiku", "--strict-mcp-config"], input=prompt, capture_output=True, text=True, timeout=280).stdout
        l = json.loads(re.search(r"\[.*\]", o, re.S).group(0))
        return list(zip(batch, l)) if len(l) == len(batch) else []
    except Exception: return []
def run(sample):
    with ThreadPoolExecutor(4) as ex: return [x for r in ex.map(stance, [sample[i:i+50] for i in range(0, len(sample), 50)]) for x in r]
out = {}
for name, s in (("posted", sa), ("liked", sb)):
    r = run(s); c = Counter(l for _, l in r); pol = c["left"] + c["right"] + c["center"]
    print(f"{name}: n={len(r)} {dict(c)} | among stance-taking: left {c['left']/pol:.0%} right {c['right']/pol:.0%} center {c['center']/pol:.0%}")
    out[name] = [{"text": p["text"][:280], "label": l, "uri": p.get("uri") or f"at://{p['did']}/app.bsky.feed.post/{p['rkey']}"} for p, l in r]
json.dump(out, open("data/stance-sample.json", "w"))
print("\nright-labelled samples:"); [print("  -", " ".join(x["text"].split())[:150]) for x in random.sample([x for x in out["posted"] if x["label"] == "right"], min(10, sum(x["label"] == "right" for x in out["posted"])))]

# (2) follows among sampled active users
lists = [l.rstrip("\n").split("\t")[1].split(",") for l in open("data/graph/follows.tsv") if "\t" in l]
indeg = Counter(x for fs in lists for x in set(fs))
known = """thebulwark.com sarahlongwell.bsky.social billkristol.bsky.social davidfrum.bsky.social tomnichols.bsky.social jonathanvlast.bsky.social timmiller.bsky.social
adamkinzinger.substack.com joewalsh.bsky.social georgeconway.bsky.social ruthbenghiat.bsky.social mattyglesias.bsky.social noahpinion.bsky.social joshbarro.bsky.social
reason.com cato.org thedispatch.com nationalreview.com jonahgoldberg.bsky.social freepress.bsky.social washingtonexaminer.com nypost.com foxnews.com wsj.com
whitehouse.gov gop.bsky.social jessesingal.com tyler-cowen.bsky.social""".split()
print("\nknown accounts: followers | sampled active users following (of", len(lists), ")")
for h in known:
    try: p = call("app.bsky.actor.getProfile", actor=h); print(f"  @{p['handle']:32} {p.get('followersCount',0):>8} {indeg[p['did']]:4}")
    except Exception: print(f"  @{h:32} (not found)")
# (3) bios
Q = ["conservative", "republican", "maga", "trump supporter", "america first", "libertarian", "centrist", "moderate", "pro-life", "patriot christian"]
seen = {}
for q in Q:
    for a in paginate("app.bsky.actor.searchActors", "actors", max_items=300, q=q): seen.setdefault(a["did"], a)
dids = list(seen); prof = {}
for i in range(0, len(dids), 25):
    for p in call("app.bsky.actor.getProfiles", actors=dids[i:i+25])["profiles"]: prof[p["did"]] = p
top = sorted(prof.values(), key=lambda p: -p.get("followersCount", 0))[:220]
prompt = ("For each Bluesky account bio, say whether the person describes THEMSELVES as politically right, center, or libertarian. Anti-MAGA people, journalists covering conservatives, and left accounts are 'no'. "
          "Return ONLY JSON {\"<handle>\": \"right\"|\"center\"|\"libertarian\"|\"no\"}.\n\n" + json.dumps({p["handle"]: (p.get("description") or "")[:150] for p in top}))
o = subprocess.run(["claude", "-p", "--model", "haiku", "--strict-mcp-config"], input=prompt, capture_output=True, text=True, timeout=280).stdout
lab = json.loads(re.search(r"\{.*\}", o, re.S).group(0))
print("\nself-described non-left accounts, by followers (of", len(prof), "profiles matched):")
for p in top:
    l = lab.get(p["handle"], "no")
    if l != "no": print(f"  {l:11} {p.get('followersCount',0):>8} in-sample {indeg[p['did']]:3} @{p['handle'][:30]:30} {(p.get('description') or '')[:70]!r}")
