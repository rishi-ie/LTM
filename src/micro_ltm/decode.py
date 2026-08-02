from __future__ import annotations

import numpy as np

from .schemas import DecoderResult, Label

LABELS: tuple[Label, ...] = ("entailed", "contradicted", "unknown")
LABEL_INDEX = {x: i for i, x in enumerate(LABELS)}


def features(state: np.ndarray, codes: np.ndarray, query: int) -> np.ndarray:
    return np.asarray([float(state @ codes[0, query]), float(state @ codes[1, query])], dtype=np.float64)


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=1, keepdims=True)


class LogisticDecoder:
    def __init__(self, weights: np.ndarray, bias: np.ndarray):
        self.weights = weights.astype(np.float64)
        self.bias = bias.astype(np.float64)

    def probabilities(self, x: np.ndarray) -> np.ndarray:
        x = np.atleast_2d(x).astype(np.float64)
        return _softmax(x @ self.weights + self.bias)

    def predict(self, x: np.ndarray) -> DecoderResult:
        p = self.probabilities(x)[0]
        index = int(np.argmax(p))
        return DecoderResult(LABELS[index], tuple(float(v) for v in p))


def train_decoder(
    x: np.ndarray,
    labels: list[str],
    learning_rate: float = 0.05,
    l2: float = 0.001,
    epochs: int = 500,
    patience: int = 40,
) -> LogisticDecoder:
    y = np.zeros((len(labels), 3), dtype=np.float64)
    y[np.arange(len(labels)), [LABEL_INDEX[v] for v in labels]] = 1.0
    w = np.zeros((2, 3), dtype=np.float64)
    b = np.zeros(3, dtype=np.float64)
    mw = np.zeros_like(w); vw = np.zeros_like(w)
    mb = np.zeros_like(b); vb = np.zeros_like(b)
    best_w, best_b, best_loss = w.copy(), b.copy(), float("inf")
    stale = 0
    for t in range(1, epochs + 1):
        p = _softmax(x @ w + b)
        loss = -float(np.mean(np.sum(y * np.log(np.maximum(p, 1e-12)), axis=1))) + l2 * float(np.sum(w * w))
        if loss < best_loss - 1e-9:
            best_loss, best_w, best_b, stale = loss, w.copy(), b.copy(), 0
        else:
            stale += 1
        if stale >= patience:
            break
        gw = (x.T @ (p - y)) / len(labels) + 2.0 * l2 * w
        gb = np.mean(p - y, axis=0)
        for param, grad, m, v in ((w, gw, mw, vw), (b, gb, mb, vb)):
            m[...] = 0.9 * m + 0.1 * grad
            v[...] = 0.999 * v + 0.001 * grad * grad
            param[...] -= learning_rate * (m / 0.1) / (np.sqrt(v / 0.001) + 1e-8)
    return LogisticDecoder(best_w, best_b)
