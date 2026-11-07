"""Hand corrections to model tags, each checked against the account's summary."""
import json
L = "US left: anti-Trump partisan"; E = "Entertainment, comedy and fandom"
FIX = {"jerilryan.bsky.social": E, "opinionhaver.bsky.social": E, "drannieandrews.com": L, "naugtynonnie.bsky.social": L,
       "realinfowars.bsky.social": E, "sonambulismo.cc": "Brazilian left", "wolfpack11720.bsky.social": L, "matchbox30.bsky.social": "US left: progressive movement", "grueloflaw.bsky.social": L, "nytpitchbot.bsky.social": L}
# Satire and left-on-left criticism that the model read as right-wing.
LEAN = {"matchbox30.bsky.social": "left", "sonambulismo.cc": "left", "realinfowars.bsky.social": "none", "regimecpa.bsky.social": "none"}
import sys
p = sys.argv[1] if len(sys.argv) > 1 else "data/top-accounts-tags.json"; rows = json.load(open(p))
for a in rows:
    if a["handle"] in FIX:
        a["category"] = FIX[a["handle"]]
    if a["handle"] in LEAN: a["lean"] = LEAN[a["handle"]]
# The anti-Trump second pass offers only three choices, so it puts some left-leaning anti-Trump reposters in "moderate".
# A moderate must not lean left; send those back to the anti-Trump left.
moved = 0
for a in rows:
    if a.get("category") == "US moderate or centrist" and a.get("lean") == "left": a["category"] = L; moved += 1
json.dump(rows, open(p, "w")); print("overrides applied:", len(FIX), "| left-leaning 'moderates' moved:", moved)
