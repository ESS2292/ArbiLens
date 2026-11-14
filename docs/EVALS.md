# Evaluation

`arbilens eval` compares two strategies on a labeled set and writes `eval/reports/latest.json` and `eval/reports/latest.md`. `--check` exits 1 when `eval/thresholds.json` fails. GitHub Actions runs that command.

The command always uses the offline fake embedding provider and the extractive reader. The report's `provider` field is `fake`.

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

Citation faithfulness. A question counts when every citation's offsets satisfy `document[start:end] == citation.text` and at least one citation contains the gold evidence sentence. This is not a natural-language inference model.

Offset integrity. The fraction of questions whose citations are exact slices. An empty citation list is vacuously intact. The upgraded and baseline readers both copy real sentences, so this number should stay at 1. A drop means the binder is wrong.

Risk-flag accuracy. The fraction of contracts whose predicted code set equals the gold set. Risk-flag F1 is micro precision and recall over the codes. Flags come from the deterministic rubric applied to whatever clauses the strategy extracted, so a bad span can change a flag. A heading window that says "Limitation of Liability" but does not contain "unlimited" will not raise `uncapped_liability`, and it will also not raise `missing_liability_cap`.

## Reading the current numbers

On this set, with the fake provider, the upgraded strategy scores 1.000 on the headline metrics. That is not a claim about neural legal reasoning. It means:

- the gold clauses are the numbered sections, and the clause-aware chunker keeps those sections intact
- every gold section contains the marker the tagger looks for
- the gold risk codes are exactly what the rubric emits from those sections
- the fake reader quotes the evidence sentence when retrieval puts that clause in the shortlist
- the semantic questions were written against the concept list the fake embedder uses

The baseline is not at zero. Type F1 stays high because headings still fall inside some window. Recall@5 and faithfulness are 0.500 because the lexical questions that fit in a window are answerable, and the semantic and straddling questions are not. Span F1 collapses because a 320-character window cannot cover the longer gold clauses at IoU 0.5. `payment_terms` is the exception: one short payment clause was aligned to a window on purpose.

If those sentences were rewritten so the markers and the concept list no longer matched, the upgraded score would fall. The gate would fail, which is what it is for.

## Reproduce

From the repository root, after the quickstart install:

```bash
arbilens eval
arbilens eval --check
```

Thresholds compare values rounded to three decimal places, the same precision as the table. `upgraded` entries are floors. `min_delta_over_baseline` entries are the minimum gap. Offset integrity is floored at 1.0. Type F1 is floored for the upgraded strategy and is not required to beat the baseline by a wide margin, because the baseline is supposed to detect types from headings.

Update `eval/thresholds.json` and the README table in the same change as any dataset or metric edit. `backend/app/tests/test_eval_harness.py` checks that the README contains the table the code just printed.
