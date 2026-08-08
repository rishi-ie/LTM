# I2 — Multiscale Minimap Latent Dynamic Inference

## Measured classification

**I2-C — LOCAL TRANSITION FAILURE**

The supplied-Mumbrane implementation reached the local-transition fail-fast
boundary. The learned kernel was trained and evaluated on all 6,000 configured
development queries. It produced no accepted exact candidates and did not
recover the required body frontier, so the specification does not authorize
deep composition, intervention, cache, or naturalistic claims.

| Metric | Development result | Gate |
| --- | ---: | ---: |
| Cases | 6,000 | 6,000 |
| Accepted precision | 0.0000 (0 accepted) | >=0.95 |
| Safe coverage | 0.0000 | >=0.85 |
| Answerable exactness | 0.0000 | >=0.90 |
| One-step exactness | 0.0000 | >=0.95 |
| Required-body frontier recall | 0.0005 | 1.00 |
| Incorrect accepted | 0 | 0 |
| Converged trajectories | 0.5002 | >=0.99 |
| Energy-increase/backtracking events | 5,045 | 0 |

The model checkpoint contains 73,985 trainable parameters (below the 2M
limit), and the minimap accounting itself completed: 48,000 training bodies,
24,000 development bodies, and 100,000 locked bodies were partitioned into
hashed hierarchical cells. The failure is therefore not a representation-size
or dataset-construction pass; it is a failure to learn a useful local
transition/frontier signal from the anonymous body configurations.

The 12,000-query locked continuation was intentionally stopped after the
development gate failed, before prediction shards were emitted. This is a
fail-fast result, not a fabricated locked score. The frozen checkpoint and
development metrics remain available in the authoritative workspace.

## Interpretation

I2 does **not** show that a fixed prompt anchor plus movable state and
multiscale minimaps are impossible in general. It shows that this particular
relation-free transition kernel did not recover even one-step body completion
well enough to justify testing long paths. The next engineering boundary is
local transition representation/training (directional displacement,
multi-input completeness, and context gates), not decoder quality. I1's
relation-free local field result and G2.5's supplied-atom compiler remain
historical and unchanged.

Authoritative workspace: `workspaces/ltm-inference-i2-r1/`.
