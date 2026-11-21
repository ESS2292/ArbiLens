# Evaluation data provenance

The contracts in `contracts/` and the labels in `labels.json` were written for this repository. They are original text. They are not copied from a published, commercial, or public-domain agreement, and they are not excerpts of anyone else's form.

`contracts/` is the dev set. `tuning/` is the development set used to choose heading, stemming, and fusion changes. It includes the three short contracts that were inspected while the first held-out set was being diagnosed, plus four extra notes written to exercise heading styles. `heldout/` is a later set of twelve contracts and forty-eight questions. It was written and committed before those pipeline changes. Its gold spans were chosen by reading the text, using the rules in `docs/EVALS.md`. They are not chunker output and they were not revised after the pipeline changed.

The held-out files cover these variations: an `Article IV — Compensation` heading, roman-numeral articles, lettered `(a)` `(b)` subsections, ALL-CAPS headings, unnumbered title-case headings, headings written on the same line as the body, a long run-on section, one sentence that states two obligations, distractor sentences, paraphrased questions, and singular/plural wording (`invoice` in the contract, `invoices` in the question). Each question records `heading_style`. Morphology items also set `variation` to `morphology`. The question `kind` stays inside the loader's existing values so the frozen file loads without a code change.

The files are covered by the repository's MIT license (Copyright (c) 2026 Emilio Straubel).

Several sections include short boilerplate sentences ("Headings in this section are for convenience of reference..."). Those sentences make the gold clause longer than the 320-character baseline window, so the fixed-window strategy cannot contain the whole clause. The operative sentences, the questions, and the risk labels were written by hand and checked against the rubric in `backend/app/engine/risks.py`.

Gold clause spans are the clause text itself. The loader finds each quote in the file and rejects a label that is missing or repeated. Character offsets are derived from that lookup; they are not transcribed by hand.
