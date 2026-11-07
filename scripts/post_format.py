"""Classify a post into one mutually exclusive format bucket."""
import re
from urllib.parse import urlparse

URL = re.compile(r"https?://\S+|\b[\w-]+\.(com|org|net|io|social|app|gg|co|uk|jp|tv|me|be)\b/?\S*", re.I)
GIF_HOSTS = ("klipy.com", "tenor.com", "giphy.com")

def fmt(p):
    e = (p.get("embed") or "").replace("app.bsky.embed.", ""); text = p.get("text") or ""
    plain = URL.sub(" ", text); n = len(" ".join(plain.split()))
    host = urlparse(p["ext"]).netloc if p.get("ext") else ""
    if e == "video": return "Video"
    if e == "images": return "Images, no text" if n == 0 else "Images with text"
    if e == "recordWithMedia": return "Quote post with media"
    if e == "record": return "Quote post"
    if e == "external": return "GIF" if host.endswith(GIF_HOSTS) else "Link card"
    if URL.search(text): return "Text with bare link"
    if n < 40: return "Text: under 40 characters"
    if n < 140: return "Text: 40–139 characters"
    if n < 250: return "Text: 140–249 characters"
    return "Text: 250+ characters"
