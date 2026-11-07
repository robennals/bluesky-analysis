# A map of what's on Bluesky (2026-10-29)

**Summary:** About half of what's posted in English is casual conversation. The rest is mostly US politics, entertainment fandom, bots, hobbies, adult content, and artists sharing work. It isn't all angry politics and porn, but a large share is. US politics and news are 13% of posts, and adult content is 6%. Substantive writing is a thin layer. About 4% of English posts are long and original (roughly 90,000 a day across the network), and even within that layer, politics and personal posts dominate. Tech, research, history and economics together are about 15% of the long posts, roughly 14,000 a day. Valuable posters exist, but they are too rare to find by random sampling. Finding them has to go through who follows whom and through known seed people. Other atproto apps write only 0.37% of all records; Bluesky is 99.6%.

## Method
- **Sample:** 17 two-minute slices, one every 2 hours from 10-28 14:41 UTC to 10-29 22:41 UTC, replayed from Jetstream. That gave 847k events and 85,676 posts. Script: `scripts/jetstream-slots.mjs`.
- **Post clusters:** English posts were embedded with model2vec (`potion-base-32M`) and clustered with k-means (k=40). Each cluster is described automatically by its distinctive words, hashtags, link sites, author concentration and most central posts. Script: `scripts/cluster_posts.py`; output: [clusters-raw.md](clusters-raw.md).
- **Account clusters:** each account's posts were averaged into one embedding, which washes out tone, and then clustered (k=30). This used the 1,784 accounts with at least 3 posts in the sample. Script: `scripts/cluster_accounts.py`; output: [accounts-raw.md](accounts-raw.md).
- **Categories:** the 40 clusters were grouped into broad categories by hand. The mapping is in `scripts/macro_shares.py`.
- **Long-form layer:** top-level English posts of at least 250 characters, from accounts that are not heavy posters. These were clustered separately (k=20); output: [clusters-long.md](clusters-long.md).
- **Other apps:** `scripts/app_share.py`.

## What's posted (unique English posts of 25 characters or more)
| Share | Category |
|---|---|
| 40.2% | Casual chat, banter, emotions (mostly replies) |
| 13.0% | US politics and news (midterms in 5 days; overwhelmingly anti-Trump) |
| 11.0% | Entertainment and fandom (TV, film, games, streams; Patrick Stewart's death) |
| 9.8% | Bots, spam, automated feeds (moderation-ban logs, stock and crypto tickers, Japanese affiliate adverts, AI-generated "tips" threads) |
| 8.7% | Hobbies and interests (music, sports, food, cities and transit) |
| 6.3% | Adult content |
| 5.5% | Artists sharing work and compliments |
| 3.3% | Non-English text mislabelled as English |
| 2.3% | Tech, software, game development |

Across all posts, including non-English: English 61%, unlabelled 12%, Japanese 9%, Portuguese 3%, Spanish 3%, German 3%.

## Who posts often (account clusters)
- **About half of frequent posters are conversational:** chat, affection, venting.
- **About 15% post mostly about US politics or world news.**
- **Smaller groups:** sports, music radio, finance and economics, transit, data and weather bots, an open-source and Linux technical group (2.2%), and Portuguese and Dutch/German speakers.

## The long-form layer (about 90,000 posts a day)
- **Politics:** about 30% (opinions, election and voting, world affairs).
- **Personal life, feelings, and requests for help:** about 30%.
- **Entertainment, streaming and fandom:** about 15%, including tributes to Patrick Stewart.
- **Code and apps; history, research and books; economy and budgets; world news digests:** about 5% each.

## Other apps on the protocol
- **Bluesky is 99.63% of records created; everything else is 0.37%.**
- **75 other namespaces were seen.** The largest: Standard.site (long-form documents), Afrilingua (language learning), Currents (saves), Tangled (code), Gainforest (conservation), Rocksky and teal.fm (music logs), Spark (video), Delvetown (AI agents).

## Caveats
- **The sample is 34 minutes over 1.5 days, during an unusual news week:** the midterms are 5 days away, and Patrick Stewart has just died.
- **Short posts cluster by tone as much as by topic.** The category shares depend on my hand mapping.
- **model2vec is a fast, lightweight embedding model.** A stronger model, plus a language model labelling each cluster, would give cleaner topics.

## Getting historical data
- **The live stream (Jetstream) replays about 36 hours.** I measured this on 10-29; asking for 48 or more hours back returned events from 10-28 12:31 UTC.
- **Any one account's full history is public.** It can be read page by page through the AppView (`getAuthorFeed`), or downloaded as the account's whole repository from its host server (`com.atproto.sync.getRepo`). Deleted records are not included.
- **The whole network's history means downloading about 47M repositories:** terabytes of data and days of work. It's possible, but not needed for phase 1. Published academic datasets cover 2023–2025. Daily aggregate statistics are at bsky-search.jazco.io/stats.
- **Searching posts needs a logged-in account.**

## Update: what is read, and the follow graph (2026-10-29, evening)
**Summary:** Likes are extremely concentrated, but following is not. The interactive page is [bluesky-map.html](bluesky-map.html), built by `scripts/build_viz.py` from `data/viz-data.json`.

- **Likes:** 47% of posts get zero likes. The top 0.1% of posts get 30% of all likes, the top 1% get 56%, and the top 10% get 85%. This is measured on 67,333 sampled posts, counted at least 12 hours after posting.
- **Who gets liked:** in the 2-minute windows, the top 1% of authors received 31% of likes, and the top 0.1% received 13%.
- **Following is flat:** in the complete follow lists of 1,988 random active posters (median 247 follows each), the top 1,000 accounts receive only 6% of follows. 71% of followed accounts are followed by just one person in the sample.
- **Posted vs liked, by category:** politics is liked more than it's posted (1.3×), as are art (3.5×) and adult content (3.7×). Bots (0.8×) and non-English text mislabelled as English (0.4×) are liked less. Casual conversation is about even.
- **Communities (4,000 core accounts, 20 groups):**
  - **By members:** the largest are gaming/comics/animation creators, celebrities and fandom, and US Democratic politics and cable news.
  - **By core accounts:** 14 of the 20 are political. Dense follow-for-follow networks (for example "Blue Crew") hold hundreds of core accounts but few of the sampled members.
- **Convergence:** the 20-group communities are **not** stable at about 2,000 users.
  - **Different random seeds on the same data agree at 0.63–0.84** (adjusted Rand index).
  - **Disjoint half-samples of about 1,000 users agree at only 0.28,** and 800 vs 1,988 users at 0.43.
  - **Coarser groupings converge faster:** with 6 groups, seeds agree at 0.97 and half-samples at 0.53.
  - **So sample size is the limit.** A stable 20-group map likely needs 5,000–10,000 sampled users. Script: `scripts/convergence_seeds.py`.
- **Labelling:** a single Sonnet call labelled the topics (cached in `data/topics-stage1.json`). Haiku labelled the communities.

## Update: community hierarchy and post formats (2026-10-30)
- **Hierarchy:** the 20 communities merge into five top-level groups, using average linkage on their audience centroids (`scripts/hierarchy.py`). Haiku named them (`scripts/label_parents.py`). Five is the most stable cut on disjoint half-samples (adjusted Rand index 0.54, versus 0.28 for 20 groups).
- **The five groups (sampled members / core accounts):**
  - Celebrities, comedy and commentary (461 / 798)
  - Grassroots left-leaning community (243 / 2,116)
  - National politics and law (229 / 737)
  - Gaming, comics and animation (229 / 129)
  - UK and global news (109 / 220)
- **Formats:** posts with images or video are 16% of posts and 56% of likes. 70% of link-card posts get no likes. 49% of posts are replies, and they collect 22% of likes. Script: `scripts/formats.py`.
- **Likes per account:** results are pending `scripts/account_likes.py`; `scripts/account_summary.py` then summarizes them.

## Update: Left politics umbrella (2026-10-30)
- **Structure:** a Haiku reading of each community's top accounts and posts (`scripts/political_lens.py`) marked 16 of 20 communities as left and political. `scripts/reorganize.py` places them under a Left politics umbrella, with four groups: Grassroots anti-Trump Democrats (243 members), Mainstream US politics and law (229), Policy and tech journalism (155), British left commentary (50). Outside it: Celebrities, comedy and fandom (306), Gaming and animation creators (229), Global news and Ukraine coverage (59).
- **Scale:** the umbrella holds 53% of the 1,265 users who could be assigned to a community, which is 34% of all 1,988 sampled users. The other 723 follow fewer than 5 core accounts and aren't assigned anywhere.
- **Method note:** the umbrella is a model judgement of political content. The audience groups underneath come from the follow graph. Three communities moved out of their audience groups to sit under it.

## Correction: the "Global news and Ukraine" community (2026-10-30)
- **Renamed "Mainstream and international news".** Its top accounts are mainly general news outlets. In a sample of 96 of their English posts, 14% mention US politics terms, 4% mention Ukraine or Russia, and 16% mention other international topics.
- **The Ukraine signal came from two member accounts:** 70 of the 85 Ukraine-related member posts. Only 21 of its 59 members had English posts in the sample.
- **Earlier claim withdrawn:** "their distinctive politics is pro-Ukraine, 26% of political posts" reflected those two accounts, not the community.
- **General lesson:** a community is defined by who its members follow, not by what they post. Model-written names can over-read a few loud members.

## Likes to the top 1,000 accounts (2026-10-30)
- **About 34% of English likes go to the 1,000 most-liked accounts,** and about 16% to the top 100, in the 34 sampled minutes. The denominator is all likes × the 79% English share, because accounts of unknown language are mostly small. Using only known accounts would give an inflated 51%.
- **Across all languages:** 29% of likes go to the top 1,000 accounts, out of 122,763 liked accounts.
- **Compare:** the top 1,000 accounts by follows get about 7% of follows and about 19% of English likes.

## Likes per account (2026-10-30)
Likes received over 30 days by 1,267 random English active accounts, counting every post and reply. Reweighted because frequent posters were more likely to be sampled (`scripts/account_likes.py`, `scripts/account_summary.py`).
- **Concentration:** the top 1% of accounts get 37% of likes, the top 10% get 73%, and the top half get 98%. Post-level concentration is higher: the top 1% of posts get 57%.
- **Typical account:** median 287 likes in 30 days; 90th percentile 3.7K; 99th 32K; 1% received none.
- **What predicts likes:** log posts-per-30-days correlates 0.75 with log likes; log followers correlates 0.64.
- **Limits:** 193 accounts hit the 1,200-item fetch cap and are undercounted, and 76 accounts failed to fetch. With 1,267 accounts, the top 0.1% figure rests on about one account, so it's left out.

## Who gets the attention (2026-10-30)
37,039 English accounts that posted during the sample, ranked by likes received in the 34 sampled minutes (`scripts/attention_compare.py`). The page's attention section is now one curve with a measure toggle, plus this comparison.

| | Top 1% (370) | Next 9% | Other 90% |
|---|---|---|---|
| Share of likes | 51% | 33% | 17% |
| Share of posts | 1.7% | 12.4% | 85.8% |
| Likes per account | 180.5 | 13.0 | 0.7 |
| Median followers | 27K | 3.9K | 624 |
| Median accounts followed | 1.3K | 904 | 377 |
| Median lifetime posts | 21K | 14K | 2.8K |
| Median account age | 3.3 years | 3.0 years | 2.0 years |

- **Content:** top 1% vs other 90%: politics 19% vs 11%; images 23% vs 13%; video 5.5% vs 1.7%; bots 2% vs 6%.
- **Limit:** ranking on a short window favours whoever is being liked at that moment, so the 51% runs above the 30-day figure of 37%.

## Rebuilt on 30 days (2026-10-30)
Replaces the window-based comparison, which counted only 24% of likes. Script: `scripts/attention_30d.py`. Stratified sample of 1,822 English accounts, the most-liked seen plus a random draw, weighted to an estimated 111,972 active accounts (posted in 30 days and seen posting or being liked in the sample). The 2-hour collection stopped at 2,439 of 3,000 accounts: the head stratum is complete and the tail is a random 939.

| | Top 0.1% (111) | Top 1% (~1,066) | Next 9% | Other 90% |
|---|---|---|---|---|
| Share of likes | 17% | 38% | 34% | 28% |
| Share of posts | 0.3% | 2.3% | 16.4% | 81.3% |
| Median followers | 109K | 96K | 5.9K | 750 |
| Median following | 1.7K | 899 | 515 | 397 |
| Median posts, 30 days | 535 | 405 | 205 | 85 |
| Replies | 32% | 54% | 59% | 60% |

- **Half of likes go to about 3,150 active accounts (top 2.8%).** The top 1,000 get about 37%.
- **Withdrawn:** "top accounts aren't celebrities (27K followers)", "the top 0.1% follow 8.3K accounts", and "51% to the top 1%". All were window artifacts.
- **Top 1,000 cliques (by likes):** anti-Trump left 41%, progressive 8%, expert left 5%; left-leaning overall 61%, right 0.1%.
- **Limits:** the top-1,000 list comes from the 1,500 most liked in our minutes and misses some accounts that were quiet then; 380 heavy posters hit the fetch cap, so the top is undercounted; tail accounts carry a weight of about 104, so small differences aren't meaningful.

## Anti-Trump, not left (2026-10-30)
A second Haiku pass over 294 accounts (`scripts/retag_anti_trump.py`) separated "Anti-Trump, not left" (Never-Trump conservatives and former Republicans) from the US left and from true moderates. Seven tags were then corrected by hand (`scripts/tag_overrides.py`). After that, only one account remains tagged moderate.

## Correction: right-leaning accounts (2026-10-30)
All four accounts tagged right-leaning were wrong, and were corrected by hand (`scripts/tag_overrides.py`): a left critic of moderate Democrats, The Onion's satirical InfoWars, a Brazilian satirist, and an accountant. No account among the 1,500 tagged is now marked right. The model misreads satire and left-on-left criticism as right-wing, so the check here was one-directional: only right-tagged accounts were reviewed.

## Scale comparison (2026-10-30)
Figures and sources are in `viz/scale.json`. Daily: Threads 147M, Reddit 130.3M, X 123.7M, Bluesky 3M (Similarweb mobile; Reddit is company-reported and includes logged-out visitors). Bluesky posters 0.6M a day. Monthly: X 302M, Bluesky 10.4M, Mastodon about 0.8M; no reliable Truth Social figure exists. Weekly posts: Bluesky about 24.6M, r/AskReddit 1.07M, r/politics 164K. Reddit blocks automated requests, so subreddit figures are from a third-party tracker.

## Instagram and TikTok added to scale (2026-10-30)
Instagram: 2B daily (Meta earnings call, July 29, 2026), 3B monthly (Zuckerberg, September 2025). TikTok publishes no global figures: about 1B daily and 2B monthly are outside estimates, labelled weak on the page. Threads: 500M monthly (same Meta call). Company figures and Similarweb mobile estimates aren't directly comparable.

## Facebook added to scale (2026-10-30)
Facebook: 2.11B daily and 3.07B monthly are Meta's last official figures, from December 2023; on the July 2026 earnings call Zuckerberg said only "more than 2 billion daily actives for a while now".

## Open networks (2026-11-06)
Bluesky is not non-commercial: it is run by Bluesky Social PBC, a venture-backed public benefit corporation, on an open protocol. Among open networks it is by far the largest: 10.4M monthly app users, against a fediverse total of about 1.42M (Mastodon 0.84M, Pixelfed 0.31M, PeerTube 0.06M, Lemmy 0.03M; fedistats.cyfinoid.com, Nov 5, 2026) and Nostr about 13K monthly (profilestr.com, Nov 6, 2026).

## Where a random like goes (2026-11-06)
1,000 random likes on English posts; the 870 authors were tagged with the top-1,000 pipeline (`scripts/like_sample.py`, `scripts/like_sample_cliques.py`). Shares are ±3 points or less.
- **Left-wing politics:** 36% of random likes vs 55% of the top 1,000's likes. US anti-Trump left 23% vs 41%.
- **Adult content:** 14% vs 7%. Art 14% vs 8%. Entertainment 13% vs 9%. Video games 6% vs 2%.
- **No account in the sample is tagged right-wing.**
- **Fix:** anyone tagged moderate whose posts lean left is moved back to the anti-Trump left (`scripts/tag_overrides.py`). The second pass offers only three choices, so it misplaced 8 such accounts.
