# TakeMeter

A fine-tuned text classifier that evaluates **discourse quality** in [r/soccer](https://www.reddit.com/r/soccer/) by classifying each comment as `analysis`, `hot_take`, or `reaction`.

See [planning.md](planning.md) for the full design rationale.

## Community

r/soccer (~8.7M subscribers). Match threads skew toward emotional reaction, tactical posts toward argument, and transfer threads toward bold unbacked claims — so "what kind of discourse is this comment" is a distinction regulars recognize and argue about.

## Labels

| Label | One-sentence definition |
| --- | --- |
| `analysis` | Makes a specific, checkable observation or argument about how/why something happened (concrete events, patterns, stats, mechanisms). |
| `hot_take` | A bold, confident opinion stated without supporting evidence — asserts rather than argues. |
| `reaction` | An immediate emotional response, celebration, joke, or banter — little to no argument. |

**Decision rule (applied in order):** `analysis` if it gives specific evidence → else `hot_take` if it's a strong claim with no evidence → else `reaction`. The `hot_take`/`analysis` line is *evidence*; the `hot_take`/`reaction` line is *whether a claim is made at all*.

## Data Collection

Reddit blocks programmatic requests from datacenter IPs (HTTP 403), so data was collected from a browser:

1. Open a r/soccer thread, append `.json` to the URL, save the page into `data/`.
2. Flatten it to CSV: `python fetch_reddit.py parse data/<file>.json`
   (`fetch_reddit.py` also has `listing` / `thread` fetch commands for when run on a residential network, plus `browser_snippet.js` for grabbing comments via the DevTools console.)

Collected from 4 thread types to cover the full range of discourse:

| Thread type | Comments | Skews toward |
| --- | ---: | --- |
| Post-match thread (Australia 2–0 Türkiye) | 159 | `reaction` |
| Tactical analysis (WC2026 4-4-2 trends) | 54 | `analysis` |
| Transfer/opinion (Julián Álvarez) | 183 | `hot_take` |
| Daily Discussion | 180 | mixed |

~576 raw comments collected. After filtering low-content comments (<5 words, emoji-only, bot boilerplate) and deduping → 507 candidates (`annotate_prep.py`).

## Labeling Process

A labeling batch of 254 candidates was drawn across thread types, **weighted toward the analysis-rich threads** (not uniform) so the scarce `analysis`/`hot_take` classes would clear 20%. Each comment was labeled by applying the ordered decision rule in [planning.md](planning.md).

**AI assistance (disclosed):** the 254 examples were pre-labeled by an LLM (Claude, Opus 4.8) applying the decision rule, then reviewed by the human annotator. `labeled_dataset.csv` is the post-review result. Per planning.md, the LLM is *not* counted as an independent annotator for any inter-annotator-reliability work.

The dataset is saved as **one complete file**, `labeled_dataset.csv` (columns `text, label, notes, thread_type, id`) — **not pre-split**; the training notebook does the 70/15/15 split. The `notes` column documents the genuinely difficult cases.

**Label distribution (no class above 70% — no imbalance problem):**

| Label | Count | % |
| --- | ---: | ---: |
| reaction | 101 | 40% |
| analysis | 83 | 33% |
| hot_take | 70 | 28% |
| **total** | **254** | |

**Hard-to-label examples:** see the "Difficult Cases Encountered During Annotation" section of [planning.md](planning.md) — including the `ot9hf47` vs `ot91oen` pair (same facts, opposite labels, decided by framing).

## Models

**Fine-tuned model:** `distilbert-base-uncased`, fine-tuned for sequence classification (3 labels) on the 177-example training split via the HuggingFace `Trainer` on a Colab T4 GPU. Best checkpoint selected on validation accuracy.

**Baseline:** zero-shot `llama-3.3-70b-versatile` (Groq), prompted with the label definitions + one example each and asked to output exactly one label per comment. No task-specific training. (See the prompt in the notebook; built directly from planning.md.)

### Key hyperparameter decision: epochs (and learning rate)

The most consequential decision was **training length**, and it took an explicit iteration:

- **First attempt — defaults (3 epochs, lr 2e-5, batch 16):** *failed.* With 177 examples ÷ batch 16 ≈ 12 steps/epoch, 3 epochs is only **~36 gradient updates**. Training loss never left the random-guess value (≈ ln 3 = 1.10), and the model **never predicted `hot_take` once** (per-class F1 = 0.00). Fine-tuned accuracy (0.615) came in *below* the baseline — classic underfitting on a small dataset.
- **Second attempt — 10 epochs, lr 3e-5, batch 16:** *fixed it.* ~120 gradient updates let training loss fall to ~0.09 and revived all three classes. This is the model reported below.

Takeaway: on a small dataset, epoch count matters more than the default suggests — *number of gradient steps*, not epochs alone, is what the model needs. `batch_size` was left at 16 (fine for 177 examples) and `lr` nudged 2e-5 → 3e-5 to help the model move within the limited steps.

## Results

### Baseline — zero-shot `llama-3.3-70b-versatile` (Groq)

Evaluated on the locked 39-example test set, before any fine-tuning. All 39 responses parsed (0 unparseable).

- **Accuracy: 0.718**
- **Macro-F1: 0.68**

| Label | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| analysis | 0.65 | 0.85 | 0.73 | 13 |
| hot_take | 0.80 | 0.40 | 0.53 | 10 |
| reaction | 0.76 | 0.81 | 0.79 | 16 |

**Reflection / hypothesis (to test after fine-tuning):** the baseline's weakness is the `analysis`↔`hot_take` boundary, exactly as anticipated in planning.md. `hot_take` recall is only 0.40 while `analysis` over-fires (recall 0.85, precision 0.65) — i.e. the model misreads confident, evidence-free opinions as `analysis` because they *sound* substantive. `reaction` is the easiest class. Hypothesis: fine-tuning should improve `hot_take` recall most, since the model can learn that assertiveness without evidence is a `hot_take`, not analysis.

### Fine-tuned model vs. baseline

Both evaluated on the **same locked 39-example test set**. (Raw numbers in `evaluation_results.json`; fine-tuned confusion matrix image in `confusion_matrix.png`.)

| Metric | Zero-shot baseline (70B) | Fine-tuned DistilBERT | Δ |
| --- | ---: | ---: | ---: |
| **Accuracy** | **0.718** | 0.667 | −0.051 |
| **Macro-F1** | **0.68** | 0.66 | −0.02 |

**Per-class F1 (baseline → fine-tuned):**

| Label | Baseline P / R / F1 | Fine-tuned P / R / F1 | F1 change |
| --- | --- | --- | --- |
| analysis | 0.65 / 0.85 / 0.73 | 0.80 / 0.92 / **0.86** | ↑ +0.13 |
| hot_take | 0.80 / 0.40 / 0.53 | 0.43 / 0.60 / 0.50 | ≈ −0.03 |
| reaction | 0.76 / 0.81 / 0.79 | 0.80 / 0.50 / 0.62 | ↓ −0.17 |

**Fine-tuned confusion matrix** (rows = true, columns = predicted; diagonal = correct):

| true ↓ \ pred → | analysis | hot_take | reaction |
| --- | ---: | ---: | ---: |
| **analysis** | **12** | 1 | 0 |
| **hot_take** | 2 | **6** | 2 |
| **reaction** | 1 | 7 | **8** |

#### Headline result

Fine-tuning on 177 examples **did not beat the zero-shot 70B baseline** — accuracy 0.667 vs 0.718, macro-F1 0.66 vs 0.68 (a gap of 2 test examples, within noise on a set this small). By the success criteria in planning.md ("must beat zero-shot on macro-F1"), fine-tuning **did not clear the bar** overall. This is the honest, informative outcome of the baseline comparison: a small fine-tuned model does not surpass a large general model on this subjective task with only 177 training examples.

It is **not** a uniform regression, though: `analysis` detection improved markedly (F1 0.73 → 0.86). The cost shows up in the confusion matrix — the model now **over-predicts `hot_take`**, swallowing 7 of 16 `reaction`s, which is what drags overall accuracy below the baseline.

#### Error-pattern analysis (AI-assisted, then hand-verified)

Per the AI Tool Plan in [planning.md](planning.md), I gave the full list of misclassifications to an LLM and asked it to surface systematic patterns, then verified each by re-reading the examples (I discarded one proposed pattern — "fails on long comments" — which re-reading did not support; error length was mixed). The pattern that held up is **directional**:

- **Which labels are confused — the boundary the model hasn't learned: `reaction` → `hot_take`.** 7 of the 13 errors (54%) are reactions predicted as hot_takes; every other off-diagonal cell has ≤ 2. One dominant, directional failure mode.
- **Why that boundary is hard:** it's *tone vs. structure*. The misclassified reactions are opinionated, charged banter (*"...sooner turkey go out the better"*, *"11 F-22s vs 11 entrenched kangaroos"*) — they *sound* like takes but argue no disputable football claim. The model keys on assertive tone; the label depends on whether a real claim is actually made.
- **Labeling problem or data/boundary problem?** I re-checked the 7 misclassified reactions against the decision rule — they were labeled *consistently* (charged banter with no disputable claim = `reaction`), so this is **not annotation inconsistency**. It's the boundary being genuinely fuzzy plus too few boundary examples: with 70 `hot_take`s and limited charged-but-claimless `reaction`s, the model never learned that tone ≠ stance. A second human annotator might reasonably dispute a few of these — which is exactly why inter-annotator agreement would be informative here.
- **What would fix it:** more labeled examples on the `reaction`/`hot_take` border — especially opinionated banter that is *not* a take — so the model learns to require a disputable claim, not just an assertive tone. A sharper operational cue in the definition (e.g., "a `hot_take` must name a specific football subject *and* make a claim about it") would help both annotators and the model.

Notably, the failure mode **moved**: the 70B baseline's weak spot was `analysis`↔`hot_take`; fine-tuning largely fixed that (analysis F1 0.73 → 0.86, only 1 analysis→hot_take error) but introduced the new `reaction`→`hot_take` over-prediction. The model traded one boundary confusion for another.

#### Three errors analyzed

1. **`reaction` → `hot_take` (confidence 0.86):** *"Didn't stay up for this but a nice result to wake up to. Get in Australia, sooner turkey and the booing cunts go out the better."* This is celebration/banter (a `reaction`), but it carries an opinionated charge ("sooner they go out the better"), so the model read it as a take. The model latched onto *opinionated tone* as a `hot_take` signal, missing that no disputable football claim is actually argued — exactly the `reaction`/`hot_take` line we had to tighten in the planning stress-test.
2. **`hot_take` → `analysis` (confidence 0.88):** *"That's not really fair to Foden imo. He rarely played for City for most of the season and never really made a peep, publicly at least..."* This sits genuinely on the boundary — it offers mild reasons ("rarely played", "never made a peep"), so the model called it `analysis`. Our annotation labeled it `hot_take` because the reasons are vague and unverifiable rather than concrete evidence. The model can't yet distinguish *real* evidence from *gestures at* evidence — the hardest distinction in the taxonomy.
3. **`analysis` → `hot_take` (confidence 0.65):** *"Didnt we take the 424 from Hungarians actually? Their managers, like Bela Guttman, were even here to show us, I thought?"* A genuine historical/tactical point (a named manager, a specific formation), phrased as a tentative question. The model misread the casual, question-form phrasing as an opinion. It over-weights *assertive vs. tentative tone* and under-weights *concrete factual content*.

#### What the model learned vs. what I intended

I intended the model to separate the three classes by **evidence** (`analysis` vs `hot_take`) and **whether a disputable claim is made** (`hot_take` vs `reaction`). What it actually learned is closer to a **tone detector**:

- It learned `analysis` well (F1 0.86) — concrete, evidence-bearing comments have a recognizable style, and the model picked it up. Our pre-training hypothesis that fine-tuning would lift `hot_take` recall also held (0.40 → 0.60).
- But it largely keys on **assertiveness/opinionated tone** rather than the underlying *evidence* and *disputability* tests. So it tags opinionated reactions as `hot_take` (error 1), tentative-sounding analysis as `reaction`/`hot_take` (error 3), and vague gesturing as `analysis` (error 2). The distinction my taxonomy is built on — *is there real evidence, and is a real claim being made* — is more semantic than 177 examples can teach a small model, especially across the `hot_take` boundary, which even the 70B baseline found hardest.

In short: fine-tuning produced a competent `analysis` detector but a tone-driven, over-eager `hot_take` classifier, and on this dataset that nets out just below a strong zero-shot baseline. The most likely path to actually beating the baseline is **more labeled data** (especially clean `hot_take`/`reaction` boundary cases), not more training on the existing 177.

#### Sample classifications (fine-tuned model)

Five test comments run through the fine-tuned model, with predicted label and the model's confidence:

| Comment (truncated) | Predicted | Confidence | Correct? |
| --- | --- | ---: | :-: |
| "…attack in a 4-2-3-1 or 4-3-3, Germany even uses a crazy 3-1-6 in attack (which makes them vulnerable to counters)…" | `analysis` | 0.97 | ✅ |
| "Talk shit get fucking dog walked you cunts" | `reaction` | 0.96 | ✅ |
| "And made fun of RM, only to have Bernardo Silva and Cucurella snatched away from them. It's all so embarrassing." | `hot_take` | 0.88 | ✅ |
| "Didn't stay up for this but a nice result to wake up to. Get in Australia, sooner turkey and the booing cunts go out the better." | `hot_take` | 0.86 | ❌ (true `reaction`) |
| "Didnt we take the 424 from Hungarians actually? Their managers, like Bela Guttman, were even here to show us, I thought?" | `hot_take` | 0.65 | ❌ (true `analysis`) |

**Why the first prediction is reasonable:** the comment names a specific formation (3-1-6) and gives a mechanistic consequence ("makes them vulnerable to counters") — concrete, checkable tactical reasoning, which is precisely the `analysis` definition. The model assigns it 0.97, its highest-confidence band, for the right reason.

**Calibration note:** the model is confidently right on clear cases (0.96–0.97) but also confidently *wrong* on the `reaction`/`hot_take` boundary (0.86 on row 4). High confidence is not a reliable signal of correctness on the hardest boundary — relevant for any deployment that surfaces confidence to users.

## Repository

| File | Purpose |
| --- | --- |
| `planning.md` | Label design, definitions, decision rules, edge cases, eval plan, AI tool plan. |
| `labeled_dataset.csv` | The 254 labeled examples (`text, label, notes, thread_type, id`), not pre-split. |
| `fetch_reddit.py` | Fetch / parse Reddit data into flat CSV. |
| `browser_snippet.js` | DevTools console grabber (alternative collection method). |
| `annotate_prep.py` | Filter + dedupe raw comments into a candidate pool. |
| `build_dataset.py` | Apply labels + difficult-case notes, emit `labeled_dataset.csv`. |
| `data/` | Flattened per-thread `.csv` files and candidate pool. |
| `*_thread.json`, `daily_discussion.json` | Raw browser `.json` exports (provenance). |
| `evaluation_results.json` | Accuracy metrics for both models (output from Colab). |
| `confusion_matrix.png` | Fine-tuned model confusion matrix (output from Colab). |
