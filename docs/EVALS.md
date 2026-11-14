# Evaluation

`arbilens eval` scores two splits and writes `eval/reports/latest.json` and `eval/reports/latest.md`. `--check` exits 1 when `eval/thresholds.json` fails. GitHub Actions runs that command.

Both splits use the offline fake embedder, the extractive reader, and the deterministic faithfulness judge. The gate does not call `ARBILENS_JUDGE_PROVIDER`.

## Labeling rules

Labels are chosen by reading the contract. They are not the output of `chunk_clause_aware` or the marker tagger. A test checks that at least one held-out gold span is not equal to any clause-aware chunk.

A gold clause is the contiguous text a reader would call one operative provision. It may be a sentence inside a longer section. The span is the exact quote stored in the label file. Offsets are resolved by finding that quote, and the loader rejects a quote that is missing or repeated.

Clause type is the legal job of that quote: a damages ceiling is `limitation_of_liability` even when it never says those words. A quote that states two jobs is two gold clauses, even when they share a sentence.

A question's `evidence` is the quote that contains the fact. A question's `claim` is a paraphrase and must not occur verbatim in the contract. `distractor` questions put the question's words in a different section. `paraphrase` questions avoid the evidence's distinctive words. `lexical`, `semantic`, and `straddle` are the dev-set kinds: shared words, concept-list synonyms, and a sentence placed across a 320-character window.

Risk labels are the trigger rules in `backend/app/engine/risks.py` applied by hand to the gold clause text, not to whatever the tagger returned. A test re-runs the code on that gold text to catch transcription mistakes. If the tagger misses a liability clause, the system emits `missing_liability_cap` and the gold set does not.

## Splits

`eval/data/labels.json` is the dev set: six contracts written so numbered headings and marker words agree with the pipeline. `eval/data/heldout.json` is three contracts written afterward. Provenance for both is in `eval/data/PROVENANCE.md`.

## Strategies

| Name | Chunking | Retrievers | Reranker |
| --- | --- | --- | --- |
| baseline | fixed windows, 320 characters, no overlap | BM25 | off |
| upgraded | clause headings the detector knows, otherwise one span until the next known heading | BM25 + fake embeddings, RRF with k = 60 | lexical bonus |

Known headings are `Section 4. Liability`, `2. Payment Terms`, and `4) Payment Terms`. `Article IV — Payout` and `Ownership of new drawings` are not headings. Text under them stays in the previous chunk.

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
| upgraded | clause headings, split only inside a long clause | BM25 + fake embeddings, RRF with k = 60 | lexical bonus |

## Metrics

Retrieval. A chunk is relevant when it contains the full gold evidence string. Recall@5 is the fraction of questions whose relevant chunk is in the top 5. MRR is the mean of `1 / rank` of the first relevant chunk, or 0 when none is relevant.

Clause span precision, recall, and F1. A prediction matches a gold clause of the same type when the intersection over union of the two character spans is at least 0.5. Matching is greedy, one gold span per prediction. The headline number is micro F1 across types. The report also lists per-type F1.

Clause type F1. Same matching, but any positive overlap counts. A window that caught the heading and only part of the clause is a type hit and a span miss.

Citation faithfulness. Offsets must satisfy `document[start:end] == citation.text`, and the deterministic judge must accept the paraphrased claim. A word in the claim counts when the quote contains it or when both sides trigger the same concept. Digits in the claim must appear in the quote. "No ceiling" contradicts "shall not exceed". The judge fails closed: a paraphrase outside the concept list is unfaithful. It also fails open on a run-on quote that happens to contain every fact in the claim, which is the Willow case. Set `ARBILENS_JUDGE_PROVIDER=openai` to send the same claim and quotes to an OpenAI-compatible chat endpoint. That judge is not used for the gate, and it can be wrong in the ordinary way a model is wrong.

Offset integrity. The fraction of questions whose citations are exact slices. An empty citation list is vacuously intact. The upgraded and baseline readers both copy real sentences, so this number should stay at 1. A drop means the binder is wrong.

Risk-flag accuracy. The fraction of contracts whose predicted code set equals the gold set. Risk-flag F1 is micro precision and recall over the codes. Flags come from the deterministic rubric applied to whatever clauses the strategy extracted, so a bad span can change a flag. A heading window that says "Limitation of Liability" but does not contain "unlimited" will not raise `uncapped_liability`, and it will also not raise `missing_liability_cap`.

## Reading the current numbers

Dev scores of 1.000 mean the numbered sections, the markers, and the concept list still agree. Held-out scores are the check on that agreement.

On the held-out set the upgraded rank-1 recall is 0.400, below the baseline's 0.600. Span F1 is 0.000 for both. Faithfulness is 0.600 for both. The thresholds do not require the upgrade to beat the baseline on this split. They freeze the measured upgraded numbers, including that 0.400, so a later change cannot quietly drop them.

Recall@5 is a weak number here because each held-out contract has about four chunks. A miss still fits in the top five. Recall@1 and the faithfulness judge are the numbers that move.

Concrete misses on the upgraded path:

- `bramble-payout`. The question asks what Bramble Goods can be asked to pay when an ordinary accident happens. `2. Credits` uses those words and is cited. The cap is the sentence under `Article IV — Payout`, which is not a detected heading, so it sits inside `1. Orders`. The sentence also lacks every liability marker, so the rubric reports `missing_liability_cap`. The judge rejects the credit quote.
- `yarrow-owner`. The question asks who keeps the pictures made for this assignment after the bill is settled. `2. Tools` repeats that wording and is cited. The drawings sentence is under `Ownership of new drawings`, inside `1. Grant`. The word "assignment" in the distractor is also tagged as an assignment clause.
- `willow-days` and `willow-cover`. Payment and the covering promise are one sentence. The gold spans are the two halves. Neither matches the section chunk at IoU 0.5. The citation is the whole sentence, so both paraphrases look supported. Faithfulness passes while span F1 stays zero. "invoice" does not match the marker "invoices", so the payment half is not tagged either.

## Reproduce

From the repository root, after the quickstart install:

```bash
arbilens eval
arbilens eval --check
```

Thresholds compare values rounded to three decimal places, the same precision as the table. Dev `min_delta_over_baseline` requires the upgrade to keep its lead on that split. Held-out `min_delta_over_baseline` is empty: the upgrade is not ahead there, and the gate does not pretend it is. Held-out floors are the measured upgraded numbers, so rank-1 recall cannot fall below 0.400 without a threshold edit.

Update `eval/thresholds.json` and the README table in the same change as any dataset or metric edit. `backend/app/tests/test_eval_harness.py` checks that the README contains the table the code just printed.
