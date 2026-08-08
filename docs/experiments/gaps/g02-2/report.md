# G2.2 — Sentence-Level Reasoning Compiler Report

## Status

**G2.2-C-FROZEN-REPRESENTATION-INSUFFICIENT / G2.2-H-NOT-DEMONSTRATED**

This result is bounded to controlled unseen language in the G1 ontology. It does not establish
unrestricted language ingestion, latent optimization, decoder quality, or 100M-context reliability.

## Locked measurements

- Operational candidate: `partial-0010`
- Runtime: 58.958 seconds
- Peak RSS: 967.7 MB
- Network calls: 0

## Gates

- `all_case_exact`: fail
- `ambiguity`: pass
- `direction`: fail
- `link_coverage`: fail
- `link_precision`: fail
- `memory`: pass
- `no_cross_session`: pass
- `no_full_scan`: pass
- `no_silent_invalid`: pass
- `quarantine`: pass
- `relation_f1`: fail
- `relation_roles`: fail
- `runtime`: pass
- `scope_time`: fail
- `sentence_coverage`: fail
- `sentence_precision`: fail
- `span_f1`: fail
- `span_offsets`: fail

## Method metrics

### frozen-0003

- Sentence: `{"accepted_exact_precision": 0.0, "all_case_exact": 0.0, "ambiguity_recall": 1.0, "direction_accuracy": 0.4035, "disposition_accuracy": 0.46425, "high_severity_polarity_errors": 0.0, "polarity_accuracy": 1.0, "quarantine_recall": 1.0, "relation_macro_f1": 0.026764385621462123, "relation_role_exact": 0.2, "safe_coverage": 0.0, "scope_time_accuracy": 0.4115, "silent_invalid_insertions": 0.0, "span_f1": 0.02694571615434925, "span_offset_accuracy": 0.024652943992340835}`
- Link: `{"complete_topology_scans": 0.0, "cross_session_links": 0.0, "link_exact": 0.0, "link_exact_precision": 0.0, "link_safe_coverage": 0.0}`

### frozen-0010

- Sentence: `{"accepted_exact_precision": 0.0, "all_case_exact": 0.0, "ambiguity_recall": 1.0, "direction_accuracy": 0.45625, "disposition_accuracy": 0.52125, "high_severity_polarity_errors": 0.0, "polarity_accuracy": 1.0, "quarantine_recall": 1.0, "relation_macro_f1": 0.034057376320429024, "relation_role_exact": 0.2, "safe_coverage": 0.0, "scope_time_accuracy": 0.4865, "silent_invalid_insertions": 0.0, "span_f1": 0.06998913961626645, "span_offset_accuracy": 0.06941120153183342}`
- Link: `{"complete_topology_scans": 0.0, "cross_session_links": 0.0, "link_exact": 0.0, "link_exact_precision": 0.0, "link_safe_coverage": 0.0}`

### nonrecurrent

- Sentence: `{"accepted_exact_precision": 0.0, "all_case_exact": 0.0, "ambiguity_recall": 1.0, "direction_accuracy": 0.42875, "disposition_accuracy": 0.51325, "high_severity_polarity_errors": 0.0, "polarity_accuracy": 1.0, "quarantine_recall": 1.0, "relation_macro_f1": 0.031957629839685565, "relation_role_exact": 0.2, "safe_coverage": 0.0, "scope_time_accuracy": 0.449, "silent_invalid_insertions": 0.0, "span_f1": 0.04099153567110036, "span_offset_accuracy": 0.040569650550502635}`
- Link: `{"complete_topology_scans": 0.0, "cross_session_links": 0.0, "link_exact": 0.0, "link_exact_precision": 0.0, "link_safe_coverage": 0.0}`

### partial-0003

- Sentence: `{"accepted_exact_precision": 0.0, "all_case_exact": 0.0, "ambiguity_recall": 1.0, "direction_accuracy": 0.27675, "disposition_accuracy": 0.297, "high_severity_polarity_errors": 0.0, "polarity_accuracy": 1.0, "quarantine_recall": 1.0, "relation_macro_f1": 0.03900135283443963, "relation_role_exact": 0.2, "safe_coverage": 0.0, "scope_time_accuracy": 0.2805, "silent_invalid_insertions": 0.0, "span_f1": 0.023249477794932343, "span_offset_accuracy": 0.015318334131163236}`
- Link: `{"complete_topology_scans": 0.0, "cross_session_links": 0.0, "link_exact": 0.0, "link_exact_precision": 0.0, "link_safe_coverage": 0.0}`

### partial-0010

- Sentence: `{"accepted_exact_precision": 0.0, "all_case_exact": 0.0, "ambiguity_recall": 1.0, "direction_accuracy": 0.28875, "disposition_accuracy": 0.30475, "high_severity_polarity_errors": 0.0, "polarity_accuracy": 1.0, "quarantine_recall": 1.0, "relation_macro_f1": 0.04974896796159173, "relation_role_exact": 0.2, "safe_coverage": 0.0, "scope_time_accuracy": 0.30475, "silent_invalid_insertions": 0.0, "span_f1": 0.06497997815799053, "span_offset_accuracy": 0.04272379128769746}`
- Link: `{"complete_topology_scans": 0.0, "cross_session_links": 0.0, "link_exact": 0.102, "link_exact_precision": 0.102, "link_safe_coverage": 0.136}`

