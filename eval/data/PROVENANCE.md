# Evaluation data provenance

The contracts in `contracts/` and the labels in `labels.json` were written for this repository. They are original text. They are not copied from a published, commercial, or public-domain agreement, and they are not excerpts of anyone else's form.

`contracts/` is the dev set. `heldout/` is a second set written after the pipeline existed. Its gold spans were chosen by reading the text. They are not chunker output. A test fails if every held-out gold span equals a clause-aware chunk.

The files are covered by the repository's MIT license (Copyright (c) 2026 Emilio Straubel).

Several sections include short boilerplate sentences ("Headings in this section are for convenience of reference..."). Those sentences make the gold clause longer than the 320-character baseline window, so the fixed-window strategy cannot contain the whole clause. The operative sentences, the questions, and the risk labels were written by hand and checked against the rubric in `backend/app/engine/risks.py`.

Gold clause spans are the clause text itself. The loader finds each quote in the file and rejects a label that is missing or repeated. Character offsets are derived from that lookup; they are not transcribed by hand.
