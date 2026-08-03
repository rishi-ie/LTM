# G2.1 — Frozen Reasoning Embedding Kernel

G2.1 tests whether the local frozen `all-MiniLM-L6-v2` semantic encoder can
support topology-compatible relation classification when paired with a small
linear or nonlinear multi-head classifier. It covers all G1 relations with two
or three supplied argument spans. It excludes clause extraction, free-form
generation, latent-field construction and decoding.

The locked result is valid only after development selection is frozen. A pass
authorizes a later clause-extraction experiment; it does not establish full
natural-language topology compilation.

Implementation resources: [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), [Sentence Transformers encoding API](https://www.sbert.net/docs/sentence_transformer/usage/usage.html), [PyTorch cross entropy](https://docs.pytorch.org/docs/stable/generated/torch.nn.CrossEntropyLoss.html), and [supervised contrastive learning](https://proceedings.neurips.cc/paper/2020/hash/d89a66c7c80a29b1bdbab0f2a1a94af8-Abstract.html).
