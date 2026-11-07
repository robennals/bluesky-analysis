"""Tiny unauthenticated Bluesky AppView client with on-disk caching."""
import json, os, time, urllib.parse, urllib.request, hashlib

BASE = "https://public.api.bsky.app/xrpc/"
CACHE = os.path.join(os.path.dirname(__file__), "..", "data", "cache")
os.makedirs(CACHE, exist_ok=True)

def call(method, **params):
    q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}, doseq=True)
    path = os.path.join(CACHE, hashlib.sha1(f"{method}?{q}".encode()).hexdigest() + ".json")
    if os.path.exists(path):
        return json.load(open(path))
    for attempt in range(5):
        try:
            with urllib.request.urlopen(BASE + method + "?" + q, timeout=30) as r:
                data = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(5 * (attempt + 1)); continue
            raise
        except Exception:  # dropped connection / truncated body (IncompleteRead)
            time.sleep(2 * (attempt + 1))
    else:
        raise RuntimeError(f"giving up on {method}")
    json.dump(data, open(path, "w"))
    return data

def paginate(method, key, max_items=2000, **params):
    out, cursor = [], None
    while len(out) < max_items:
        d = call(method, cursor=cursor, limit=100, **params)
        out += d.get(key, [])
        cursor = d.get("cursor")
        if not cursor: break
    return out
