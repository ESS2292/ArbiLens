# Evaluation

`arbilens eval` scores the dev, tuning, and held-out splits and writes `eval/reports/latest.json` and `eval/reports/latest.md`. `--check` exits 1 when `eval/thresholds.json` fails. GitHub Actions runs that command.

Parameters are chosen on dev and tuning only. The held-out set is never used to pick a heading rule, a marker, a fusion weight, or a threshold. Thresholds are updated after a change is frozen, to the numbers that change just measured. `eval/reports/previous-upgraded.json` is the upgraded pipeline from before the heading, stemming, and fusion changes, scored on the same frozen files.

Both splits use the offline fake embedder, the extractive reader, and the deterministic faithfulness judge. The gate does not call `ARBILENS_JUDGE_PROVIDER`.

## Labeling rules

Labels are chosen by reading the contract. They are not the output of `chunk_clause_aware` or the marker tagger. A test checks that at least one held-out gold span is not equal to any clause-aware chunk.

A gold clause is the contiguous text a reader would call one operative provision. It may be a sentence inside a longer section. The span is the exact quote stored in the label file. Offsets are resolved by finding that quote, and the loader rejects a quote that is missing or repeated.

Clause type is the legal job of that quote: a damages ceiling is `limitation_of_liability` even when it never says those words. A quote that states two jobs is two gold clauses, even when they share a sentence.

A question's `evidence` is the quote that contains the fact. A question's `claim` is a paraphrase and must not occur verbatim in the contract. `distractor` questions put the question's words in a different section. `paraphrase` questions avoid the evidence's distinctive words. `lexical`, `semantic`, and `straddle` are the dev-set kinds: shared words, concept-list synonyms, and a sentence placed across a 320-character window.

Risk labels are the trigger rules in `backend/app/engine/risks.py` applied by hand to the gold clause text, not to whatever the tagger returned. A test re-runs the code on that gold text to catch transcription mistakes. If the tagger misses a liability clause, the system emits `missing_liability_cap` and the gold set does not.

## Splits

`eval/data/labels.json` is the dev set: six contracts written so numbered headings and marker words agree with the pipeline. `eval/data/tuning.json` is the development set: the three contracts that were inspected while the first held-out miss was diagnosed, plus four notes used to try heading styles. `eval/data/heldout.json` is twelve contracts and forty-eight questions written and committed before the heading, stemming, and fusion changes. Provenance is in `eval/data/PROVENANCE.md`.

Held-out questions record `heading_style`: `article_emdash`, `roman`, `lettered`, `all_caps`, `title_case`, `inline`, `numbered`, `run_on`, and `combined_sentence`. Questions that change `invoice` to `invoices`, or `terminate` to a question about ending, set `variation` to `morphology` and keep a loader kind of `lexical`. The pipeline was not adjusted after those labels were read back as scores.

## Strategies

| Name | Chunking | Retrievers | Reranker |
| --- | --- | --- | --- |
| baseline | fixed windows, 320 characters, no overlap | BM25 | off |
| upgraded | clause headings, then sentence cuts inside a section longer than `clause_max_chars` | BM25 over the best sentence in each chunk, plus fake embeddings at 0.45 times the BM25 fusion weight, k = 60 | lexical bonus |

Headings are numbered lines (`2. Payment Terms`, `Section 4. Liability`, `4) Payment Terms`), `Article IV` and `Article IV — Compensation`, lettered lines such as `(a) Fees`, short ALL-CAPS lines, unnumbered title-case lines, a short sentence-case line that follows a blank line, and an inline label (`Payment terms: ...`). An inline label is a section break and not a heading, so the sentence splitter still reads the body. A section longer than the max is cut on a blank line, then a newline, then a sentence boundary. Marker matching stems tokens, so `invoice` matches `invoices` and `terminate` matches `termination`. The words `assignment`, `ownership`, `audit`, `fees`, `venue`, and `privacy` count only in the heading. `assign this agreement` still matches the body. BM25 does not use that stemmer.

## Dataset

Six original contracts live in `eval/data/contracts/`. Labels are in `eval/data/labels.json`. Provenance and license are in `eval/data/PROVENANCE.md`. Nothing in the set is copied from a published agreement.

Each contract has:

- gold clauses, stored as the clause text, with character offsets resolved by finding that text in the file
- gold risk codes from the rubric in `backend/app/engine/risks.py`
- questions, each with an evidence sentence and a kind: `lexical`, `semantic`, or `straddle`

`lexical` questions use words that appear in the evidence sentence, and that sentence fits inside one 320-character window. `semantic` questions use words that do not appear in the contract but do appear in the offline concept list (`monetary exposure` for a limitation of liability clause, for example). `straddle` questions place the evidence sentence across a window boundary, so no baseline chunk contains it.

Some sections are lengthened with ordinary boilerplate ("Headings in this section are for convenience of reference"). A 320-character window cannot cover a clause longer than 640 characters at the span threshold below. That is deliberate, and the type-level metric is there so the baseline is not described as blind.

## Strategies

| Name | Chunking | Retrievers | Reranker |
| --- | --- | --- | --- |
| baseline | fixed windows, 320 characters, no overlap | BM25 | off |
| upgraded | clause headings, sentence cuts only inside an oversized section | sentence-level BM25 + fake embeddings, embedding weight 0.45, k = 60 | lexical bonus |

## Metrics

Retrieval. A chunk is relevant when it contains the full gold evidence string. Recall@5 is the fraction of questions whose relevant chunk is in the top 5. MRR is the mean of `1 / rank` of the first relevant chunk, or 0 when none is relevant.

Clause span precision, recall, and F1. A prediction matches a gold clause of the same type when the intersection over union of the two character spans is at least 0.5. Matching is greedy, one gold span per prediction. The headline number is micro F1 across types. The report also lists per-type F1.

Clause type F1. Same matching, but any positive overlap counts. A window that caught the heading and only part of the clause is a type hit and a span miss.

Citation faithfulness. Offsets must satisfy `document[start:end] == citation.text`, and the deterministic judge must accept the paraphrased claim. A word in the claim counts when the quote contains it or when both sides trigger the same concept. Digits in the claim must appear in the quote. "No ceiling" contradicts "shall not exceed". The judge fails closed: a paraphrase outside the concept list is unfaithful. It also fails open on a run-on quote that happens to contain every fact in the claim, which is the Willow case. Set `ARBILENS_JUDGE_PROVIDER=openai` to send the same claim and quotes to an OpenAI-compatible chat endpoint. That judge is not used for the gate, and it can be wrong in the ordinary way a model is wrong.

Offset integrity. The fraction of questions whose citations are exact slices. An empty citation list is vacuously intact. The upgraded and baseline readers both copy real sentences, so this number should stay at 1. A drop means the binder is wrong.

Risk-flag accuracy. The fraction of contracts whose predicted code set equals the gold set. Risk-flag F1 is micro precision and recall over the codes. Flags come from the deterministic rubric applied to whatever clauses the strategy extracted, so a bad span can change a flag. A heading window that says "Limitation of Liability" but does not contain "unlimited" will not raise `uncapped_liability`, and it will also not raise `missing_liability_cap`.

## Reading the current numbers

Dev scores of 1.000 mean the numbered sections, the markers, and the concept list still agree. Tuning is where the sentence-level BM25 score and the 0.45 embedding weight were selected. Held-out scores were computed once after that selection. They were not used to change it.

On the current held-out set the upgraded rank-1 recall is 0.917 against a baseline of 0.792. Span F1 is 0.871 against 0.066. Faithfulness is 0.833 against 0.708. The same files, scored before the heading and fusion changes, were recall@1 0.917, span F1 0.295, and faithfulness 0.792. MRR went from 0.951 to 0.949. The thresholds freeze these upgraded numbers and the measured gaps over the current baseline.

Recall@5 is 1.000 because many of these contracts are short. Recall@1, span F1, and the faithfulness judge are the numbers that move.

Heading-style recall@1 on the upgraded held-out run is 1.000 for all-caps, roman, lettered, inline, run-on, and combined-sentence questions. Numbered questions are 0.900, title case is 0.667, and article-with-dash is 0.500. Span recall is 1.000 for all-caps, roman, inline, and title case, 0.800 for numbered, 0.750 for lettered, and 0.500 for article-with-dash and combined sentences. Assignment span F1 is 0.000 because the consent sentence shares its section with a distractor sentence, so the predicted span misses IoU 0.5. The other types are 0.500 or higher.

Concrete misses on the upgraded path, left as they measured:

- `kelp-payout`. The question asks what Kelp Goods can be asked to pay when an ordinary accident happens. `2. Credits` uses those words and is cited. The cap is now its own chunk under `Article IV — Compensation`. The judge scores the credit quote at 12% overlap. Detecting the heading did not make the lexical distractor lose.
- `morph-renew`. The question asks whether the supply renews automatically. The gold sentence says "automatic renewal". BM25 is not stemmed, the termination sentence also contains "supply", and that sentence is cited. The renewal chunk is rank 2.
- `caps-law`. The cited sentence is the gold sentence: the agreement is governed by the laws of Maine. The claim says "Maine law governs the agreement." The deterministic judge does not stem `laws`/`law` or `governed`/`governs`, so only half the claim tokens count and the claim is rejected.

## Reproduce

From the repository root, after the quickstart install:

```bash
arbilens eval
arbilens eval --check
```

Thresholds compare values rounded to three decimal places, the same precision as the table. Dev and tuning `min_delta_over_baseline` require the upgrade to keep the lead it has on those splits. Tuning does not require a recall@1 lead, because the measured recall@1 matches the baseline. Held-out floors and gaps are the numbers from the single post-change run. They were not a target while the pipeline was being changed. Rank-1 recall on that split cannot fall below 0.917, and span F1 cannot fall below 0.871, without a threshold edit. Do not edit those floors in order to make a change pass, and do not pick the change by looking at the held-out misses.

Update `eval/thresholds.json` and the README table in the same change as any dataset or metric edit. `backend/app/tests/test_eval_harness.py` checks that the README contains the table the code just printed.
