# Literature Map for Latent Topology Models

**Review date:** 2026-07-28  
**Scope:** Primary papers and official proceedings most directly relevant to the proposed LTM flow. This is a representative technical map, not a claim that every paper using related terminology has been found.

## Executive conclusion

The four LTM components are individually plausible research objects:

1. graphs, hyperbolic spaces and knowledge-graph embeddings can represent typed and directed structure;
2. energy models, associative memories and equilibrium networks can define latent fields with attractors;
3. gradient, fixed-point, stochastic and differentiable-solver methods can search those fields;
4. a separate decoder can express a selected latent or symbolic result.

There is also strong precedent for external memory, retrieval over very large corpora, differentiable logical constraints and latent reasoning.

What the literature does **not** establish is the combined LTM hypothesis:

> A configurable topology compiled from arbitrary domain data can be converted into a compact, query-conditioned field whose latent optimization performs reliable, compositional reasoning and retains an economic advantage over retrieval, graph search, constraint solvers and autoregressive reasoning.

That combined claim must be tested experimentally. In particular, convergence to a field minimum, correct retrieval and logical reasoning are different properties.

## 1. Reasoning topology

### Directed relational representations

- [TransE: Translating Embeddings for Modeling Multi-relational Data](https://papers.nips.cc/paper_files/paper/2013/hash/1cecc7a77928ca8133fa24680a88d2f9-Abstract.html) represents a relation as a translation between entity vectors. It is the simplest relevant baseline for a directed topology.
- [RotatE: Knowledge Graph Embedding by Relational Rotation in Complex Space](https://openreview.net/forum?id=HkgEQnRqYQ) represents relations as rotations and targets symmetry, antisymmetry, inversion and composition.
- [Rot-Pro](https://papers.nips.cc/paper/2021/hash/cf2f3fe19ffba462831d7f037a07fc83-Abstract.html) adds projection to better represent transitive relations.
- [Poincaré Embeddings](https://arxiv.org/abs/1705.08039) show why hyperbolic geometry can represent hierarchies more compactly than ordinary Euclidean embeddings.
- [Hierarchical Density Order Embeddings](https://arxiv.org/abs/1804.09843) connect density and order structure to graded entailment and uncertainty.

These papers support testing multiple geometries and typed relation operators. They do not show that one universal topology can encode every useful notion of reasoning.

### Multi-hop and logical queries

- [Query2Box](https://arxiv.org/abs/2002.05969) represents query answer sets as boxes and implements projection, intersection and a restricted treatment of union.
- [Neural Bellman-Ford Networks](https://proceedings.neurips.cc/paper/2021/hash/f6a673f09493afcd8b129a0bcf1cd5bc-Abstract.html) learns path-based reasoning using a generalized Bellman-Ford formulation.
- [GNN-QE](https://proceedings.mlr.press/v162/zhu22c.html) decomposes first-order logical queries into relation projections and fuzzy logical operations.
- [End-to-end Differentiable Proving](https://proceedings.neurips.cc/paper/2017/hash/b2ab001909a8a6f04b51920306046ce5-Abstract.html) makes unification differentiable by replacing discrete symbols with vector representations.

These are evidence that a topology can expose compositional operations. They also provide strong baselines: if LTM cannot beat or complement graph traversal and query embeddings on controlled relational tasks, the topology is not yet adding value.

### Calibration warning

- [The ART of Link Prediction with Knowledge Graph Embeddings](https://proceedings.mlr.press/v284/brunink25a.html) shows that scores useful for within-query ranking need not be calibrated globally.

LTM must therefore measure probability calibration and constraint validity, not just ranking metrics.

## 2. Latent dynamic field

### Energy-based formulation

- [A Tutorial on Energy-Based Learning](https://yann.lecun.org/exdb/publis/pdf/lecun-06.pdf) defines inference as assigning low energy to compatible configurations and minimizing energy over unknown variables.
- [Implicit Generation and Modeling with Energy Based Models](https://papers.nips.cc/paper_files/paper/2019/hash/378a063b8fdb1db941e34f4bde584c7d-Abstract.html) demonstrates modern neural energy models trained with MCMC.
- [Compositional Visual Generation with Energy Based Models](https://papers.nips.cc/paper/2020/hash/49856ed476ad01fcff881d57e161d73f-Abstract.html) studies composition by combining energy functions.
- [Model-Based Planning with Energy-Based Models](https://proceedings.mlr.press/v100/du20a.html) searches a learned state space between a start state and a goal.
- [Compositional Generation with Energy-Based Diffusion Models and MCMC](https://proceedings.mlr.press/v202/du23a.html) shows that the sampler itself can determine whether composed energies work.

This literature gives a clean mathematical interpretation for the LTM field. It also makes local minima, poor sampling, normalization and calibration first-class risks.

### Score and vector fields

- [Score Matching](https://jmlr.org/papers/v6/hyvarinen05a.html) learns the gradient of a log density without computing its normalization constant.
- [Sliced Score Matching](https://arxiv.org/abs/1905.07088) reduces the cost of score estimation using Hessian-vector products.
- [Score-Based Generative Modeling through Stochastic Differential Equations](https://openreview.net/forum?id=PxTIG12RRHS) learns time-dependent score fields and integrates a reverse-time stochastic process.
- [Neural Ordinary Differential Equations](https://papers.nips.cc/paper/2018/hash/69386f6bb1dfed68692a24c8686939b9-Abstract.html) parameterizes continuous latent dynamics.

An LTM implementation should initially learn a scalar energy and differentiate it. An unconstrained learned vector field can have curl, cycles or unstable dynamics and may not correspond to any coherent global objective.

### Associative memory and attractors

- [Modern Hopfield Networks and Attention](https://papers.nips.cc/paper_files/paper/2020/hash/da4902cb0bc38210839714ebdcf0efc3-Abstract.html) relates attention to a modern Hopfield update rule and analyzes high storage capacity under assumptions.
- [Universal Hopfield Networks](https://proceedings.mlr.press/v162/millidge22a.html) separates similarity, separation and projection functions and provides a broad design space for associative retrieval.
- [Associative Memories via Predictive Coding](https://papers.nips.cc/paper/2021/hash/1fb36c4ccf88f7e67ead155496f02338-Abstract.html) connects predictive-coding dynamics with associative memory.
- [Accelerating Hopfield Network Dynamics: Beyond Synchronous Updates and Forward Euler](https://proceedings.mlr.press/v255/goemaere24a.html) treats Hopfield retrieval as an ODE or equilibrium solve and compares solvers.
- [Feature Correlations Determine the Storage Capacity of Memory Models](https://openreview.net/forum?id=sbVZiZmfZ4) warns that correlated real data can sharply reduce associative-memory capacity.
- [Dense Associative Memory with Epanechnikov Energy](https://openreview.net/forum?id=ZbQ5Zq3zA3) studies retrieval capacity and unwanted emergent minima in a kernel-inspired energy.

These papers motivate direct tests of capacity, correlated memories, basin size, rare-state recall and spurious attractors.

## 3. Latent optimization

### Fixed points and implicit layers

- [Deep Equilibrium Models](https://proceedings.neurips.cc/paper/2019/hash/01386bd6d8e091c2ab4c7c7de644d37b-Abstract.html) represents an effectively infinite-depth network by a fixed point and uses root finding plus implicit differentiation.
- [DeltaDEQ](https://proceedings.neurips.cc/paper_files/paper/2024/hash/69f5b860d6dc469ac6e52f03866b73c4-Abstract-Conference.html) exploits the fact that dimensions may converge at different rates.
- [Deep Equilibrium Neural Operators](https://proceedings.neurips.cc/paper_files/paper/2023/hash/32cc61322f1e2f56f989d29ccc7cfbb7-Abstract-Conference.html) applies equilibrium ideas to steady-state operator learning.

These results support iterative latent inference, but constant activation memory does not mean constant runtime. Iteration counts and field-evaluation cost must be reported.

### Explicit optimization and satisfiability

- [OptNet](https://proceedings.mlr.press/v70/amos17a.html) inserts a differentiable quadratic-program solver into a neural network.
- [SATNet](https://proceedings.mlr.press/v97/wang19e.html) introduces a differentiable smoothed MAXSAT solver and demonstrates parity and Sudoku tasks.
- [LinSATNet](https://proceedings.mlr.press/v202/wang23at.html) embeds positive linear satisfiability constraints in a differentiable layer.
- [A Semantic Loss Function for Deep Learning with Symbolic Knowledge](https://proceedings.mlr.press/v80/xu18h.html) derives a loss measuring satisfaction of Boolean constraints.

This is strong evidence that constraint satisfaction and neural learning can be joined. It is also a warning: for problems already expressible as SAT, CSP or graph search, LTM must justify why a learned field is preferable to calling the exact solver.

## 4. Latent reasoning and the decoder boundary

- [Training Large Language Models to Reason in a Continuous Latent Space (COCONUT)](https://openreview.net/pdf?id=Itxz7S4Ip3) feeds hidden reasoning states back into a language model and reports benefits on selected search-heavy logical tasks.
- [ProofWriter](https://arxiv.org/abs/2012.13048) iterates one-step implication generation to produce checkable deductions and tests generalization to unseen proof depth.
- [Let’s Verify Step by Step](https://arxiv.org/abs/2305.20050) compares outcome and process supervision and motivates verification of intermediate reasoning.
- [Language Models Don’t Always Say What They Think](https://proceedings.neurips.cc/paper_files/paper/2023/hash/ed3fea9033a80fea1376299fa7863f4a-Abstract.html) demonstrates that generated chains of thought can be unfaithful explanations.
- [Reasoning Models Don’t Always Say What They Think](https://arxiv.org/abs/2505.05410) extends faithfulness concerns to newer reasoning models.

The LTM decoder must not be treated as proof of reasoning. Experiments must independently verify the latent state and test whether the decoder can invent a plausible answer from a wrong state.

## 5. External memory, large corpora and sparse activation

- [Improving Language Models by Retrieving from Trillions of Tokens (RETRO)](https://proceedings.mlr.press/v162/borgeaud22a.html) shows that a language model can benefit from an external database containing trillions of tokens.
- [Memorizing Transformers](https://openreview.net/pdf?id=TrjbxzRcnf-) uses approximate nearest-neighbor lookup over stored internal representations and reports gains as memory grows to 262K tokens.
- [InstructRetro](https://proceedings.mlr.press/v235/wang24bd.html) demonstrates retrieval-augmented pretraining at larger model scale.

These papers make 10–20 million tokens of **accessible storage** entirely plausible. They do not imply that all stored information can be compressed into fixed weights without loss or that every query can inspect the whole corpus at fixed cost. LTM’s relevant hypothesis is bounded sparse activation over an expandable external store.

## 6. Evaluation literature

- [CLUTRR](https://aclanthology.org/D19-1458/) tests systematic generalization of relational rules to held-out combinations and adds controlled noise.
- [ProofWriter](https://arxiv.org/abs/2012.13048) provides generated natural-language theories, deductions and proofs with controllable depth.
- [RULER](https://arxiv.org/abs/2404.06654) tests whether advertised context length translates into effective retrieval and aggregation.
- [LongBench](https://aclanthology.org/2024.acl-long.172/) covers multiple long-context tasks in English and Chinese.

The first-principles suite should use synthetic generators inspired by CLUTRR and ProofWriter before using natural-language benchmarks. This isolates topology and optimization from encoder and decoder errors.

## 7. What is established, adjacent and unproven

| Status | Claim |
| --- | --- |
| Established | Directed and hierarchical relations can be embedded, with representation-dependent trade-offs. |
| Established | Energy minimization and fixed-point iteration can perform latent inference. |
| Established | Differentiable solvers can impose logical or optimization constraints. |
| Established | External retrieval can expose models to corpora much larger than their active context. |
| Established | Latent recurrent reasoning can work on selected controlled tasks. |
| Adjacent | Modular energy functions can be composed, but optimization quality depends strongly on the sampler and landscape. |
| Adjacent | Associative fields can store many patterns under favorable assumptions, while correlations and spurious minima limit real capacity. |
| Unproven | One JSON-configurable template can express reasoning across substantially different domains. |
| Unproven | A learned field preserves enough exact topology to outperform explicit graph or solver methods. |
| Unproven | Low field energy reliably predicts semantic or logical correctness. |
| Unproven | Sparse routing preserves cross-domain reasoning while keeping active compute bounded. |
| Unproven | A small decoder can match frontier language quality without becoming the real reasoning engine. |
| Unproven | LTM reaches 10–20M-token useful memory, frontier reasoning quality or one-cent requests simultaneously. |

## Research implication

The next step is not to train a large model. It is to run small falsifiable experiments in this order:

1. prove that the chosen topology represents the required relation families;
2. prove that its explicit energy has correct and robust attractors;
3. determine whether a neural field preserves those attractors;
4. determine whether optimization reaches verified solutions;
5. prove that decoding does not hide failures;
6. compare the complete system with retrieval and exact solvers;
7. only then measure scaling.
