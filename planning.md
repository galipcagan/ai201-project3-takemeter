# TakeMeter — Planning

## Community

**r/soccer** — one of the largest football (soccer) communities on Reddit (~8.7M subscribers). Discourse is active, text-heavy, and varies enormously in quality: live match threads are pure emotional reaction, tactical posts host detailed argument, and transfer/opinion threads are full of bold, unbacked claims. The distinction between *reacting*, *asserting a take*, and *actually analyzing* is one that regulars in the community intuitively recognize and argue about constantly — which makes it a meaningful thing to measure.

## Task

Fine-tune a text classifier that labels a r/soccer comment by **what kind of discourse it is** — not whether it is "good" or "bad" (too subjective), but whether the comment *analyzes*, *asserts a take*, or *reacts*.

## Label Taxonomy (3 labels, mutually exclusive)

### `analysis`
**Definition:** Makes a specific, checkable observation or argument about how or why something happened — points to concrete events, patterns, statistics, or mechanisms.

Clear examples (from collected data):
- "Insanely impressive defense by Australia to deny Turkey... the few times they did get through, the ball fell directly into Beach's lap. Güler/Çalhanoğlu also had decent free kicks twice denied."
- "Gordon stinks against low blocks in the Prem too, so I don't know what he would offer Barcelona against a proper La Liga low block."

Uncertain example: "Fyi Anthony Gordon was playing like that for the majority of the season. The lad is utter dogshite vs lowblocks and I'm so glad I don't have to watch him." — Ranty, insult-heavy framing pulls toward `hot_take`, but it makes a *checkable* observation (a season-long pattern, specifically vs. low blocks). **Resolved to `analysis`:** the framing is harsh but the substance is a real, verifiable claim, not a bare assertion.

### `hot_take`
**Definition:** A bold, confident opinion or judgment stated without supporting evidence. The claim might be true, but the comment asserts rather than argues.

Clear examples:
- "Australia genuinely put this overrated/overpriced turkish squad in the bin."
- "Turkey disappointing once again. It's football heritage at this point."

Uncertain example: "Past few tournaments I keep hearing Turkey being hyped up, just to stink it up at the Euros and now the World Cup." — Names two tournaments, which *looks* like evidence and pulls toward `analysis`. **Resolved to `hot_take`:** the tournaments are mentioned to back a "Turkey always chokes" verdict, not to explain *how* or *why* they underperformed — the specifics are decorative, not an argument.

### `reaction`
**Definition:** An immediate emotional response, celebration, joke, or banter. Expresses a feeling in the moment with little to no argument.

Clear examples:
- "WE'RE GONNA WIN IT ALL"
- "I'd hate to be a beer in Australia right now"

Uncertain example: "We don't even have four midfielders. More like three and a half." — A witty point about squad depth that pulls toward `hot_take` (it implies a judgment). **Resolved to `reaction`:** it's a one-line quip/banter with no actual claim being argued — closer to a joke about the squad than a take on it.

## Decision Rule (resolves ambiguity & enforces mutual exclusivity)

Apply in order; a comment takes the **first** label that matches:

1. **`analysis`** — Does it give a specific, checkable reason / observation / stat for a claim? → `analysis`
2. **`hot_take`** — Is it a strong opinion or judgment with *no* supporting evidence? → `hot_take`
3. **`reaction`** — Is it just emotion, celebration, joke, or banter? → `reaction`

The dividing line between `hot_take` and `analysis` is **evidence**: a confident claim with no "why" is a `hot_take`, the same claim *with* specific support is `analysis`. The line between `hot_take` and `reaction` is **whether a disputable claim is being made**: a `hot_take` makes a claim about football that another user could rebut with "no, actually..." (player/team/decision quality, a prediction, a ranking); bare emotional venting with no specific disputable claim is a `reaction`. So "Turkey are overrated" is a take; "AUSTRALIA!!!!!" and "the ref was a disgrace today" (pure venting, no specific claim) are reactions, while "the ref cost us the game with that penalty call" is a take.

*(This "disputable claim" refinement came out of the label stress-test below — see "Label Stress-Test".)*

## Hardest Anticipated Edge Case

**"Massive upset. Hope we can keep it up against the yanks."**

Could be read as `analysis` (a judgment about the result) or `reaction` (emotional response to the win).

**Resolution:** Naming a result without explaining *why* ("massive upset", "shock defeat for turkey") is **`reaction`** — it labels the outcome but offers no observation or argument. It would only be `analysis` if it explained what made the result an upset with specifics. Per the decision rule, no evidence + no real claim → falls through to `reaction`.

## Difficult Cases Encountered During Annotation

Genuine pauses while labeling the 254 examples (each is flagged in the `notes` column of `labeled_dataset.csv`):

1. **`orl5524` — "Massive upset. Hope we can keep it up against the yanks."** → `reaction`. Labels the result without saying *why*; no evidence, no argued claim. (The anticipated hardest case above — and it did show up in the data.)
2. **`otf5vik` — "Anthony Gordon was playing like that for the majority of the season. The lad is utter dogshite vs lowblocks..."** → `analysis`. The framing is a rant, but the substance is a checkable, season-long observation. Decided that harsh tone does not downgrade a verifiable claim.
3. **`ot9hf47` vs `ot91oen` — the same facts, two labels.** Both criticize Julián Álvarez's season with specifics (penalty miss, poor La Liga form). `ot9hf47` ("ungrateful little rat... he can fuck off") → `hot_take`: accusatory rant where the stats are decorative dunks. `ot91oen` ("they lost the cdr final in part because he missed a penalty... only scored 8 league goals") → `analysis`: measured, explanatory framing. This pair was the most instructive — it forced the rule that *framing and intent*, not just presence of facts, decides `analysis` vs `hot_take`.
4. **`orypdlp` — "We don't even have four midfielders. More like three and a half."** → `reaction`. A witty squad-depth quip; it implies a judgment but argues no disputable claim, so it's banter, not a take.

## Label Stress-Test

Before relying on the taxonomy, 8 comments were generated to sit deliberately on label boundaries and run through the decision rule. 7 of 8 resolved cleanly (analysis-vs-hot_take separated by evidence; hot_take-vs-reaction separated by presence of a claim). **One broke it:** short evaluative venting — *"the ref was a disgrace today"* — sat ambiguously between `hot_take` and `reaction`, because a vented judgment is technically a "claim".

**Fix applied:** the `hot_take`/`reaction` line was tightened from "is a claim being made?" to "is a **disputable** football claim being made?" (see Decision Rule). Vented emotion with no specific, rebuttable claim is now unambiguously `reaction`. The taxonomy survived the rest of the boundary cases without further changes.

## Why these labels (vs. weak ones like good/bad)

- The boundary can be stated in one sentence (evidence test).
- Two annotators reading the definitions would agree on most examples.
- The distinction reflects how r/soccer users actually talk about discourse quality ("low-effort reaction" vs. "actual analysis" vs. "hot take").
- No single label dominates: match threads skew `reaction`, tactics posts skew `analysis`, transfer threads skew `hot_take` — so balancing across thread types yields a usable distribution.

## Data Collection Plan

**Where:** r/soccer comment threads, collected by appending `.json` to a thread URL in a browser and flattening with `fetch_reddit.py parse` (Reddit blocks programmatic fetching from datacenter IPs, so collection is browser-driven). Comments — not posts — are the unit, since the auto-generated match-info posts are templates, not discourse.

**Which threads & why:** four thread types chosen deliberately to span the discourse range, because any single thread type collapses onto one label:

| Thread type | File | Comments | Skews toward |
| --- | --- | ---: | --- |
| Post-match thread | `match_thread` | 159 | `reaction` |
| Tactical analysis | `analysis_thread` | 54 | `analysis` |
| Transfer/opinion | `transfer_thread` | 183 | `hot_take` |
| Daily discussion | `Daily_discussion` | 180 | mixed |

~576 raw comments collected. After filtering low-content comments (<5 words, emoji-only, bot boilerplate) and deduping → 507 candidates.

**How many per label:** target ≥200 labeled with **≥20% per label** (no class allowed to dominate, and well under the 70% imbalance threshold). Achieved: **254 labeled** — `reaction` 101 (40%), `analysis` 83 (33%), `hot_take` 70 (28%). Saved as one complete file `labeled_dataset.csv` (columns: `text, label, notes, thread_type, id`), **not pre-split** — the training notebook performs the 70/15/15 split automatically.

**If a label is underrepresented after 200:** `analysis` and `hot_take` are the scarce classes (match threads flood `reaction`). The fix is **targeted collection, not random sampling** — pull more analysis-heavy threads (tactics posts, post-match analysis) and opinion threads (transfers, "unpopular opinion" posts) and label only candidates likely to be the scarce class until it clears 20%. This is why the labeling batch was already weighted toward the analysis-rich threads rather than sampled uniformly.

## Evaluation Metrics

The test set is imbalanced (40/33/28), so **accuracy alone is misleading** — a model that always predicts `reaction` scores 40% while being useless. Metrics reported for **both** the fine-tuned model and the zero-shot baseline, on the same test set:

- **Macro-averaged F1 (primary metric).** Averages F1 across the three classes equally, so good performance on the majority `reaction` class can't hide failure on `analysis`/`hot_take`. This is the headline number.
- **Per-class precision and recall.** Needed to locate *where* the model fails — the expected weak spot is the `analysis`↔`hot_take` boundary (both make claims; only evidence separates them). Per-class recall tells us if a whole label is being missed.
- **Overall accuracy.** Reported because the brief requires it and it's intuitive, but read alongside macro-F1, never alone.
- **Confusion matrix.** Shows which *pairs* get confused. The hypothesis is most errors land in the `analysis`/`hot_take` cell; the matrix confirms or refutes that and drives the error analysis.

## Definition of Success

Concrete, checkable thresholds on the test set (chosen so two people could objectively agree whether they were hit):

- **Did fine-tuning do anything?** Fine-tuned model must beat *both* trivial baselines: the majority-class baseline (accuracy 0.40) **and** the zero-shot Groq baseline on **macro-F1**. If it doesn't beat zero-shot, fine-tuning added no value.
- **"Good" model:** macro-F1 **≥ 0.70**, overall accuracy **≥ 0.72**, and **no single class with recall < 0.55** (every label is usable, not just the easy ones).
- **"Good enough to deploy" in a real community tool:** macro-F1 **≥ 0.75** *and* the hardest boundary, `analysis` vs `hot_take`, achieving per-class F1 **≥ 0.65** for both. Below this, the tool would too often mislabel a bare take as analysis, defeating the point.
- **Sanity ceiling:** if accuracy exceeds **0.95** on this subjective task, treat it as a red flag (label leakage between splits, or labels too easy) and investigate before trusting it.

## AI Tool Plan

This project generates no application code, so AI tools are used in three specific places — each an explicit decision:

- **Label stress-testing (done — see "Label Stress-Test"):** an LLM was given the label definitions and edge-case rules and asked to generate comments sitting *on the boundary* between two labels. One case ("the ref was a disgrace today") could not be resolved cleanly, so the `hot_take`/`reaction` rule was tightened before relying on it. Goal met: the taxonomy was broken on purpose while it was still cheap to fix.
- **Annotation assistance (used — disclosed):** the 254 examples were **pre-labeled by an LLM (Claude, Opus 4.8)** applying the decision rule, then reviewed by the human annotator who corrected disagreements. The `labeled_dataset.csv` is the post-review result. This is disclosed here and in the README. The stretch inter-annotator-reliability feature, if done, will have a second *human* independently re-label 30+ examples to measure agreement (the LLM is not counted as the independent annotator).
- **Failure analysis (planned):** after evaluation, the list of the model's wrong predictions (true label, predicted label, text) will be given to an LLM with a prompt to find *systematic* patterns — e.g. "does it consistently misread sarcasm as analysis?", "does it fail on short comments?". Any pattern it proposes will be **verified by hand** against the actual errors before it goes in the evaluation report; unverified patterns are not reported.
