# Phase 1.1 Held-Out Results

Classification: **B**

| Method | Recall@4 | Precision@4 | Latency ms |
| --- | ---: | ---: | ---: |
| direct | 0.880 | 0.440 | 0.044 |
| mmr | 0.750 | 0.375 | 0.062 |
| mean_shift | 0.915 | 0.458 | 0.097 |
| single_latent | 0.930 | 0.465 | 0.243 |
| multi_latent | 0.885 | 0.443 | 0.915 |
| ablation_no_diversity | 0.890 | 0.445 | 0.915 |
| ablation_query_init | 0.945 | 0.472 | 0.909 |

Recall difference 95% CI: [-0.035, 0.04]
Maximum domain recall loss: 0.300
Evidence change from MMR: 0.640
Numerical failures: 0
Peak RSS: 462.7 MB
