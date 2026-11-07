# bluesky-analysis

Looking at what is going on on Bluesky, using only public data.

**The report:** [notes/bluesky-map.html](notes/bluesky-map.html) is a self-contained interactive page. Download it and open it in a browser; every chart has random samples of the real posts or accounts beside it. It covers:

- **How big Bluesky is,** compared with other social networks and other open networks.
- **Languages:** what share of posts and likes are in each.
- **Concentration of attention:** half of all likes go to about 3% of active accounts.
- **Who the most influential accounts are, and what they talk about:** the 1,000 most-liked accounts over 30 days, each tagged with its main focus. Mostly left-wing US politics.
- **What people actually like:** a random sample of likes, tagged the same way. A broader mix, spread across many more accounts.
- **Beyond Bluesky:** other apps built on the same protocol.

[notes/bluesky-topics-backup.html](notes/bluesky-topics-backup.html) holds analysis that didn't make the main page: post formats, follow-graph communities and topic clusters.

[notes/2026-10-29-bluesky-map.md](notes/2026-10-29-bluesky-map.md) is the running log of findings, methods and corrections.

## How the data was gathered

- **Posts, likes, reposts and follows:** sampled from Bluesky's public firehose (Jetstream), replaying short windows from the previous 36 hours.
- **Accounts, profiles and follow lists:** from the public Bluesky API (`public.api.bsky.app`), which needs no login.
- **30-day like counts:** read from each sampled account's own data store, weighted so the sample stands in for all active English accounts.
- **Topic tags:** a cheap model (Claude Haiku) tagged each account from its bio, its most-liked posts and what it reposts, with some hand corrections in `scripts/tag_overrides.py`.

## Rebuilding

The raw data (about 12 GB in `data/`) is not in the repo. To rebuild the page from existing data:

```bash
python3 scripts/build_viz.py   # writes notes/bluesky-map.html and notes/bluesky-topics-backup.html
```

To gather data from scratch you need Python 3 with `pip install -r requirements.txt`, Node 22 (for the Jetstream samplers in `scripts/*.mjs`), and the `claude` CLI for tagging. The page itself is built from `viz/template.html`.
