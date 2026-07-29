# Phase 1.2 Held-Out Results

Classification: **E-B**

| Method | Recall@4 | Precision@4 | Worst residual | Prompt cosine |
| --- | ---: | ---: | ---: | ---: |
| barycenter | 0.261 | 0.196 | 0.519 | 0.819 |
| density | 0.156 | 0.117 | 0.000 | 0.000 |
| direct | 0.239 | 0.179 | 0.000 | 0.000 |
| exact_equilibrium | 0.253 | 0.190 | 0.637 | 0.944 |
| hierarchical_equilibrium | 0.189 | 0.142 | 0.633 | 0.934 |
| prompt_state | 0.239 | 0.179 | 0.000 | 0.000 |

## Gate

- worst_residual_improvement: `-0.22687852463298075`
- average_residual_ratio: `1.1927639310252107`
- recall_improvement: `0.013888888888888923`
- bootstrap_recall_difference_95pct: `[-0.0055555555555555575, 0.03611111111111111]`
- minimum_prompt_cosine: `0.8698700346555679`
- minimum_hierarchy_exact_cosine: `0.9798971014422291`
- maximum_hierarchy_energy_error: `0.030462298120995726`
- mean_hierarchy_evidence_overlap: `0.7041666666666667`
- numerical_failures: `0`
- peak_rss_mb_10000: `583.640625`
- warm_optimization_ms_10000: `0.42787499842233956`
- weight_monotonic_fraction: `1.0`
- irrelevant_expansion_cosine_drift: `2.077449323678593e-12`

The experiment measures weighted semantic compatibility. It does not establish logical truth or causal reasoning.
