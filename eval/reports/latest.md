# ArbiLens evaluation

## dev

# ArbiLens evaluation

- Provider: `fake` (offline deterministic embedder and extractive reader)
- Dataset fingerprint: `f44e6bf460349996`
- Contracts: 6
- Questions: 12

Span F1 requires intersection-over-union of at least 0.5 with the gold clause.
Type F1 accepts any overlapping span of the right clause type, so a fixed window
that catches the heading still counts. Citation faithfulness requires the gold
evidence sentence to appear inside a citation whose offsets match the document.

| metric | baseline | upgraded | delta |
| --- | ---: | ---: | ---: |
| retrieval recall@1 | 0.500 | 1.000 | 0.500 |
| retrieval recall@5 | 0.500 | 1.000 | 0.500 |
| retrieval MRR | 0.500 | 1.000 | 0.500 |
| clause span F1 | 0.027 | 1.000 | 0.973 |
| clause type F1 | 0.880 | 1.000 | 0.120 |
| citation faithfulness | 0.500 | 1.000 | 0.500 |
| offset integrity | 1.000 | 1.000 | 0.000 |
| risk-flag accuracy | 0.500 | 1.000 | 0.500 |
| risk-flag F1 | 0.842 | 1.000 | 0.158 |

## Per-type span F1

| clause type | baseline | upgraded |
| --- | ---: | ---: |
| assignment | 0.000 | 1.000 |
| audit_rights | 0.000 | 1.000 |
| auto_renewal | 0.000 | 1.000 |
| confidentiality | 0.000 | 1.000 |
| data_protection | 0.000 | 1.000 |
| dispute_resolution | 0.000 | 1.000 |
| force_majeure | 0.000 | 1.000 |
| governing_law | 0.000 | 1.000 |
| indemnification | 0.000 | 1.000 |
| ip_ownership | 0.000 | 1.000 |
| limitation_of_liability | 0.000 | 1.000 |
| payment_terms | 0.250 | 1.000 |
| sla | 0.000 | 1.000 |
| termination | 0.000 | 1.000 |
| warranties | 0.000 | 1.000 |

## heldout

# ArbiLens evaluation

- Provider: `fake` (offline deterministic embedder and extractive reader)
- Dataset fingerprint: `6ebe3ba2933e7572`
- Contracts: 3
- Questions: 5

Span F1 requires intersection-over-union of at least 0.5 with the gold clause.
Type F1 accepts any overlapping span of the right clause type, so a fixed window
that catches the heading still counts. Citation faithfulness requires the gold
evidence sentence to appear inside a citation whose offsets match the document.

| metric | baseline | upgraded | delta |
| --- | ---: | ---: | ---: |
| retrieval recall@1 | 0.600 | 0.400 | -0.200 |
| retrieval recall@5 | 0.600 | 1.000 | 0.400 |
| retrieval MRR | 0.600 | 0.667 | 0.067 |
| clause span F1 | 0.000 | 0.000 | 0.000 |
| clause type F1 | 0.333 | 0.333 | 0.000 |
| citation faithfulness | 0.600 | 0.600 | 0.000 |
| offset integrity | 1.000 | 1.000 | 0.000 |
| risk-flag accuracy | 0.667 | 0.667 | 0.000 |
| risk-flag F1 | 0.941 | 0.941 | 0.000 |

## Per-type span F1

| clause type | baseline | upgraded |
| --- | ---: | ---: |
| assignment | 0.000 | 0.000 |
| indemnification | 0.000 | 0.000 |
| ip_ownership | 0.000 | 0.000 |
| limitation_of_liability | 0.000 | 0.000 |
| payment_terms | 0.000 | 0.000 |
