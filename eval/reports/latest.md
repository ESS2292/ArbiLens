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
| clause type F1 | 0.907 | 1.000 | 0.093 |
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
| payment_terms | 0.222 | 1.000 |
| sla | 0.000 | 1.000 |
| termination | 0.000 | 1.000 |
| warranties | 0.000 | 1.000 |

## tuning

# ArbiLens evaluation

- Provider: `fake` (offline deterministic embedder and extractive reader)
- Dataset fingerprint: `eb7a216b6e5ce165`
- Contracts: 7
- Questions: 13

Span F1 requires intersection-over-union of at least 0.5 with the gold clause.
Type F1 accepts any overlapping span of the right clause type, so a fixed window
that catches the heading still counts. Citation faithfulness requires the gold
evidence sentence to appear inside a citation whose offsets match the document.

| metric | baseline | upgraded | delta |
| --- | ---: | ---: | ---: |
| retrieval recall@1 | 0.846 | 0.846 | 0.000 |
| retrieval recall@5 | 0.846 | 1.000 | 0.154 |
| retrieval MRR | 0.846 | 0.887 | 0.041 |
| clause span F1 | 0.000 | 0.762 | 0.762 |
| clause type F1 | 0.800 | 0.857 | 0.057 |
| citation faithfulness | 0.769 | 0.769 | 0.000 |
| offset integrity | 1.000 | 1.000 | 0.000 |
| risk-flag accuracy | 0.714 | 0.714 | 0.000 |
| risk-flag F1 | 0.944 | 0.944 | 0.000 |

## Recall@1 by heading style

| heading style | baseline | upgraded |
| --- | ---: | ---: |
| all_caps | 1.000 | 1.000 |
| article_emdash | 0.000 | 0.000 |
| combined_sentence | 1.000 | 1.000 |
| inline | 1.000 | 1.000 |
| lettered | 1.000 | 1.000 |
| numbered | 0.000 | 1.000 |
| roman | 1.000 | 1.000 |
| title_case | 1.000 | 0.000 |

## Span recall by heading style

| heading style | baseline | upgraded |
| --- | ---: | ---: |
| all_caps | 0.000 | 1.000 |
| article_emdash | 0.000 | 0.000 |
| combined_sentence | 0.000 | 0.000 |
| inline | 0.000 | 1.000 |
| lettered | 0.000 | 0.500 |
| roman | 0.000 | 1.000 |
| title_case | 0.000 | 1.000 |

## Per-type span F1

| clause type | baseline | upgraded |
| --- | ---: | ---: |
| confidentiality | 0.000 | 1.000 |
| governing_law | 0.000 | 1.000 |
| indemnification | 0.000 | 0.000 |
| ip_ownership | 0.000 | 1.000 |
| limitation_of_liability | 0.000 | 0.000 |
| payment_terms | 0.000 | 0.800 |

## heldout

# ArbiLens evaluation

- Provider: `fake` (offline deterministic embedder and extractive reader)
- Dataset fingerprint: `6d87b3664e8d4ee0`
- Contracts: 12
- Questions: 48

Span F1 requires intersection-over-union of at least 0.5 with the gold clause.
Type F1 accepts any overlapping span of the right clause type, so a fixed window
that catches the heading still counts. Citation faithfulness requires the gold
evidence sentence to appear inside a citation whose offsets match the document.

| metric | baseline | upgraded | delta |
| --- | ---: | ---: | ---: |
| retrieval recall@1 | 0.792 | 0.917 | 0.125 |
| retrieval recall@5 | 0.792 | 1.000 | 0.208 |
| retrieval MRR | 0.792 | 0.949 | 0.157 |
| clause span F1 | 0.066 | 0.871 | 0.805 |
| clause type F1 | 0.918 | 0.968 | 0.050 |
| citation faithfulness | 0.708 | 0.833 | 0.125 |
| offset integrity | 1.000 | 1.000 | 0.000 |
| risk-flag accuracy | 0.750 | 0.833 | 0.083 |
| risk-flag F1 | 0.952 | 0.969 | 0.016 |

## Recall@1 by heading style

| heading style | baseline | upgraded |
| --- | ---: | ---: |
| all_caps | 0.800 | 1.000 |
| article_emdash | 0.500 | 0.500 |
| combined_sentence | 1.000 | 1.000 |
| inline | 0.750 | 1.000 |
| lettered | 0.750 | 1.000 |
| numbered | 0.850 | 0.900 |
| roman | 0.750 | 1.000 |
| run_on | 1.000 | 1.000 |
| title_case | 0.333 | 0.667 |

## Span recall by heading style

| heading style | baseline | upgraded |
| --- | ---: | ---: |
| all_caps | 0.200 | 1.000 |
| article_emdash | 0.000 | 0.500 |
| combined_sentence | 0.000 | 0.500 |
| inline | 0.000 | 1.000 |
| lettered | 0.000 | 0.750 |
| numbered | 0.100 | 0.800 |
| roman | 0.000 | 1.000 |
| title_case | 0.000 | 1.000 |

## Per-type span F1

| clause type | baseline | upgraded |
| --- | ---: | ---: |
| assignment | 0.000 | 0.000 |
| audit_rights | 1.000 | 1.000 |
| auto_renewal | 0.000 | 1.000 |
| confidentiality | 0.000 | 1.000 |
| data_protection | 0.000 | 1.000 |
| dispute_resolution | 0.000 | 1.000 |
| force_majeure | 0.000 | 1.000 |
| governing_law | 0.333 | 1.000 |
| indemnification | 0.000 | 1.000 |
| ip_ownership | 0.000 | 1.000 |
| limitation_of_liability | 0.000 | 0.500 |
| payment_terms | 0.000 | 0.750 |
| sla | 0.000 | 1.000 |
| termination | 0.000 | 1.000 |
| warranties | 0.000 | 1.000 |
