# L8 — Initial measured probe

The completed isolated attempt is [the ignored r6 report](../../../../Parasite-L8/var/l8-r6/report.json)
when run locally; generated workspaces are intentionally not versioned.

Measured result:

| Metric | Result |
|---|---:|
| Policy/compiler exactness | 1.00 |
| Independent evaluator agreement | 1.00 |
| Policy-twin divergence | 1.00 |
| Full minus no optimization | 1.00 |
| Full minus one sweep | 1.00 |
| Storage-order invariance | 1.00 |
| Incorrect accepted conclusions | 0 |
| Trainable parameters | 0 |
| Separate evaluator process | yes |
| Runtime | 0.81 s |

The reduced probe classified as `L8-A` within its own 16-observation vertical
boundary. This is meaningful evidence that a bounded structured reasoning
policy can alter a fixed-law equilibrium and its verified candidate without
mutating the field substrate. It is not evidence for unrestricted policy
language, arbitrary mathematics, cyclic equilibrium, unlimited hops, or the
full planned L8 suite. The next step is to expand only the case generator and
controls while freezing this runtime and policy law.
