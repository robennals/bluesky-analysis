# What social action is each liked post doing? (first pass, 2026-11-06)

**Summary:** I read 80 random liked English posts, drawn from the 1,000 random likes behind "What people actually like". For each, I asked what the post is *doing* socially and what it signals about the poster.

- **Us vs them is the biggest group (19 of 80).** Most of it is aimed at the other side, by mocking it or exposing what it did. Less of it rallies the ingroup to vote.
- **Challenges to the ingroup do happen, but they are mostly purity policing:** attacking your own side for not being pure enough. Humble self-critique showed up once.
- **Thoughtful, curious analysis is rare:** 1 to 2 posts out of 80.
- **Non-political help and teaching appear about 1 time in 16.**
- **Outside politics, the big actions are:** showing your own creative work, sexual self-display, jokes, and collective mourning (Patrick Stewart died this week).

The sample is small, so each count is accurate only to a few posts either way. The script is `scripts/social_action_sample.py`; the posts are in `data/social-action-sample.json`. The `#n` numbers below refer to positions in that file.

## Draft categories

Counts are out of 80. Some posts fit two categories; each is counted once, under the one that fits best. The tree has six top-level groups plus "can't tell". The second level is kept where the difference matters: for example, policing your own side is a different act from attacking the other.

| Category | What the post does | What it signals about the poster | Count | Examples |
|---|---|---|---|---|
| **1. Us vs them** | Takes a side in a political or cultural fight | Loyalty to a side | **19** | |
| &nbsp;&nbsp;Against the outgroup | Mocks, condemns or gloats over the other side, or exposes something outrageous it did | "They're contemptible" or "watch what they're doing" | 10 | Joke that calling a politician a clown insults clowns (#2); gloating that Google's AI is eating its own revenue (#59); Trump calls for the Alaska Senate election to be cancelled (#38); £24bn fossil-fuel subsidy (#34) |
| &nbsp;&nbsp;For the ingroup | Get out the vote, good polls, hope | Commitment and optimism | 5 | Obama heading to a Georgia rally (#68); "Democrat TIED in South Carolina" (#70); Medicare for All pitch on a rate-hike story (#14) |
| &nbsp;&nbsp;Policing the ingroup | Attacks your own side, or people near it, for not being pure enough | "I hold the line even against my own side" | 4 | "I'd prefer anti-trans Democratic candidates lose" (#10); "liberals… now demand trans people comply" (#20); donors "pulling off their democrat masks" (#50); leftist correcting a liberal on fascism (#18) |
| **2. Informing and understanding** | Adds to what people know | Curiosity, expertise, generosity | **7** | |
| &nbsp;&nbsp;Thoughtful, humble analysis | Works through an idea, admits limits, aims to understand; includes constructive self-critique of one's own side | Curiosity and fairness | 1 | "Squeezed vs struggling," using the poster's own finances, ending with how progressives could stress generosity (#51) |
| &nbsp;&nbsp;Helping or teaching, non-political | Practical advice, how-tos, history facts | Generosity and expertise | 5 | Why a TV turns itself on (#13); how to draw fabric folds (#48); a WW2 tank fact (#52); writing advice (#73) |
| &nbsp;&nbsp;Plain news | Reports without much framing | Being informed | 1 | Xi's fourth term (#58) |
| **3. Making and appreciating** | Puts work or beauty in front of people | Skill and taste | **11** | |
| &nbsp;&nbsp;Own creative work | Art, photos, comics, writing, commissions | Skill; invites appreciation | 8 | Fan art (#1, #41, #66, #74); photography (#11); "read my comics while AO3 is down" (#75) |
| &nbsp;&nbsp;Curating others' work | Shares someone else's art or a cultural artefact | Taste | 3 | A Grimshaw moonlight painting (#12); a bat painting (#43); favourite comic art (#37) |
| **4. Belonging and connection** | Maintains a relationship or a shared identity | "I'm one of you" and warmth | **16** | |
| &nbsp;&nbsp;Fandom and community games | Answering a prompt, getting excited about a release | Belonging to a fandom | 4 | Last line from a movie (#3); Hunger Games ticket (#8); a Warhammer prediction (#78) |
| &nbsp;&nbsp;Collective mourning or tribute | Shared grief for a public figure | "I loved this too" | 5 | Patrick Stewart in a lobster costume (#71); praise for his Picard (#28) |
| &nbsp;&nbsp;Personal life sharing | Life news, small moments | Openness; invites support | 4 | Losing a university job (#53); "my first gay wedding was my own" (#17) |
| &nbsp;&nbsp;Community upkeep | Thanks, greetings, gifts, congratulations | Warmth and reciprocity | 3 | Thanking an art-share host (#33); a daily greeting thread (#47) |
| **5. Entertaining** | Non-political jokes, relatable observations, pet videos | Wit; "you're like me" | **9** | Menswear joke dressed up as a culture-war line (#9); "no one says bless u anymore" (#46); "this book will not write itself" (#77) |
| **6. Sexual display or flirting** | Nude or suggestive photos, kink posts, flirting replies | Desirability; belonging to a kink community | **11** | Self-posted photos (#6, #24, #79); kink humour (#42, #56); flirty replies (#4) |
| **Can't tell: image or video only** | No text; needs the picture | — | **7** | Mostly from big accounts (5k to 22k likes), probably memes |

### Merges considered and rejected

- **Policing the ingroup into "Against the outgroup":** it attacks people on your own side, often near the edge of the group. That is the closest thing in the sample to the "challenge to its ingroup" you asked about, so it is kept visible.
- **Entertaining into Belonging:** relatable jokes do build "you're like me", but they are a large, distinct kind of content that people follow accounts for.
- **Sexual display into Making and appreciating** (much of it is drawn art): the social act differs. It is about desirability and kink community, not craft.

## Patterns worth testing on a larger sample

- **The categories you suggested are real but small.** In this sample, thoughtful analysis (1), challenging the ingroup in a humble way (1), helping people (about 5) and sharing what you've learned (part of those 5) together make up under 10% of likes.
- **Ingroup challenges come in two kinds:**
  - **Purity policing:** "my side isn't pure enough" (#10, #20, #50). This is common, and the posts are well liked: #10 got 679 likes and #20 got 710.
  - **Constructive self-critique:** "my side could do better" (#51). This is rare.
  - These are worth keeping as separate categories.
- **Political posts are mostly about the other side.** Posts against the outgroup (10) outnumber posts for the ingroup (5) 2 to 1.
- **Many posts signal belonging to a niche,** such as fandoms, kink communities, art-share circles or AO3 readers, rather than taking a stance.

## Limits

- **Small sample:** with 80 posts, a category at 10% could really be anywhere from about 4% to 16%.
- **Picture-only posts:** 7 posts have no text, and sexual or art posts are often judged from a caption alone. A larger pass needs the images.
- **One reader:** I did the labelling myself, so the categories reflect my judgement. A second labelling pass with a model would test whether they are clear enough to apply consistently.
- **Topical events:** Patrick Stewart's death and the US elections five days away inflate the mourning and rallying categories this week.

## Full run: 994 random likes, labelled by Haiku

**Summary:** Using the tree above, Claude Haiku labelled all 994 posts in the random-like sample that are still available. For each post it saw the text, the image, any quoted post or link, the thread it replies to, and the author's account tag. The page section "What liked posts are doing" in `notes/bluesky-map.html` shows the results, with random liked posts for every category and Haiku's reason for each label. The script is `scripts/social_actions.py`.

| Category | All likes | Likes on top-1,000 accounts' posts | Likes on everyone else's posts |
|---|---|---|---|
| **Us vs them** | **30%** | **54%** | **18%** |
| &nbsp;&nbsp;Against the outgroup | 24% | 43% | 15% |
| &nbsp;&nbsp;For the ingroup | 5% | 9% | 2% |
| &nbsp;&nbsp;Policing the ingroup | 1% | 2% | 1% |
| **Informing and understanding** | **7%** | **9%** | **6%** |
| &nbsp;&nbsp;Thoughtful analysis | 2% | 2% | 2% |
| &nbsp;&nbsp;Helping or teaching | 2% | 2% | 2% |
| &nbsp;&nbsp;Plain news | 3% | 5% | 2% |
| **Making and appreciating** | **11%** | **5%** | **14%** |
| **Belonging and connection** | **18%** | **12%** | **21%** |
| **Entertaining** | **13%** | **11%** | **15%** |
| **Sexual display or flirting** | **20%** | **8%** | **26%** |
| **Can't tell** | **1%** | **1%** | **1%** |

Overall shares are accurate to about ±3 points. The top-1,000 column rests on 340 likes, so it is accurate to about ±5 points.

- **Against the outgroup is the biggest single action:** a quarter of all likes and 43% of likes on the top accounts' posts. Rallying one's own side is a fifth as common.
- **The kinds of posts you asked about are rare:** thoughtful analysis 2%, helping or teaching 2%, and policing the ingroup 1%.
- **Top accounts and everyone else differ sharply.** The top accounts' likes are mostly us-vs-them. Everyone else's likes are mostly sexual content, creative work, fandom and jokes.

## How well the labels hold up

- **Agreement with the hand labels:** on the 80 hand-labelled pilot posts, Haiku picked the same top-level group 74% of the time, or 79% leaving out the 7 posts I couldn't read without the image. It picked the same sub-category 71% of the time.
- **Disagreements are mostly boundary calls:**
  - Own creative work vs fandom: fan art answering a prompt.
  - Own work vs sexual: suggestive commissioned art Haiku could see.
  - Unclear vs outgroup: images I couldn't see, which Haiku read as anti-Trump memes.
- **Two systematic misses were fixed by rerunning with a better prompt:**
  - **Mourning:** Haiku didn't know Patrick Stewart had died, so it read tributes as jokes or fandom. The prompt now gives the date and that event.
  - **Policing:** Haiku treated a leftist attacking Democrats as attacking the outgroup. The prompt now defines "own side" as the broad coalition the poster belongs to.
- **Policing is probably still undercounted.** I labelled 4 of 80 pilot posts as policing (5%); Haiku agreed on 2 of them and finds 1% overall. Whether, say, a leftist attacking liberals counts as attacking your own side is a judgement call.
