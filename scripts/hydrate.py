"""Turn post URIs and account DIDs into display-ready examples for the page."""
from concurrent.futures import ThreadPoolExecutor
from bsky import call

ADULT = {"porn", "sexual", "nudity", "sexual-figurative", "graphic-media", "gore"}

def _get(batch):
    try: return call("app.bsky.feed.getPosts", uris=batch)["posts"]
    except Exception: return []

def _example(p):
    e = p.get("embed") or {}; m = e.get("media") or e
    imgs = m.get("images") or []; thumb = (imgs[0].get("thumb") if imgs else None) or m.get("thumbnail")
    labs = {l.get("val") for l in (p.get("labels") or [])} | {l.get("val") for l in (p["author"].get("labels") or [])}
    adult = bool(labs & ADULT); r = p["record"]; ext = (m.get("external") or {})
    q = (e.get("record") or {}); q = q.get("record", q) if isinstance(q, dict) else {}
    qt = (q.get("value") or {}).get("text") if isinstance(q, dict) else None
    return {"t": (r.get("text") or "")[:280], "h": p["author"]["handle"], "n": (p["author"].get("displayName") or "")[:40],
            "l": p.get("likeCount", 0), "r": bool(r.get("reply")), "u": f"https://bsky.app/profile/{p['author']['handle']}/post/{p['uri'].rsplit('/', 1)[1]}",
            **({"i": thumb} if thumb and not adult else {}), **({"a": 1} if adult and thumb else {}),
            **({"x": ext.get("title", "")[:120]} if ext.get("title") else {}), **({"v": 1} if m.get("$type", "").startswith("app.bsky.embed.video") else {}),
            **({"q": qt[:200], "qh": (q.get("author") or {}).get("handle", "")} if qt else {}),
            **({"pu": r["reply"]["parent"]["uri"], "ru": r["reply"]["root"]["uri"]} if (r.get("reply") or {}).get("parent") else {})}

def hydrate_posts(uris):
    uris = sorted(set(uris)); out = {}
    with ThreadPoolExecutor(3) as ex:
        for ps in ex.map(_get, [uris[i:i+25] for i in range(0, len(uris), 25)]):
            for p in ps: out[p["uri"]] = _example(p)
    return out

def _latest(d):
    try:
        for i in call("app.bsky.feed.getAuthorFeed", actor=d, limit=10, filter="posts_no_replies")["feed"]:
            if "reason" not in i and i["post"]["record"].get("text"): return d, i["post"]["record"]["text"][:200]
    except Exception: pass
    return d, ""

def account_cards(dids):
    dids = sorted(set(dids)); pr = {}
    for i in range(0, len(dids), 25):
        for p in call("app.bsky.actor.getProfiles", actors=dids[i:i+25])["profiles"]: pr[p["did"]] = p
    with ThreadPoolExecutor(3) as ex: lat = dict(ex.map(_latest, dids))
    return {d: {"h": p["handle"], "n": (p.get("displayName") or "")[:40], "b": (p.get("description") or "").replace("\n", " ")[:160],
                "f": p.get("followersCount", 0), "t": lat.get(d, "")} for d, p in pr.items()}


def add_reply_context(examples):
    """For replies, attach the post being replied to and the thread's first post, so the reply makes sense.
    Replies further up the chain are not fetched; 'gap' marks that some were skipped."""
    examples = [e for e in examples if e]
    uris = {u for e in examples for u in (e.get("pu"), e.get("ru")) if u}
    raw = {}
    with ThreadPoolExecutor(3) as ex:
        uris = sorted(uris)
        for ps in ex.map(_get, [uris[i:i+25] for i in range(0, len(uris), 25)]):
            for p in ps: raw[p["uri"]] = p
    def short(u):
        p = raw.get(u)
        if not p: return {"t": "[deleted or unavailable]", "h": ""}
        e = _example(p); return {k: e[k] for k in ("t", "h", "u", "i", "a", "x", "v", "q", "qh") if k in e}
    for e in examples:
        pu, ru = e.pop("pu", None), e.pop("ru", None)
        if not pu: continue
        ctx = [short(ru)] if ru != pu else []
        ctx.append(short(pu))
        parent = raw.get(pu)
        gap = ru != pu and bool(parent) and ((parent["record"].get("reply") or {}).get("parent") or {}).get("uri") != ru
        e["ctx"] = ctx; e["gap"] = gap
    return examples
