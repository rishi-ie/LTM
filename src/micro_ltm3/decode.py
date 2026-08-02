from __future__ import annotations

import numpy as np

from micro_ltm.decode import LogisticDecoder, train_decoder

from .schemas import LatentReadout

LABELS = ("entailed", "contradicted", "unknown")


def decode_state(state: np.ndarray, positive: np.ndarray, negative: np.ndarray, decoder: LogisticDecoder) -> LatentReadout:
    x = np.asarray([float(state @ positive), float(state @ negative)], dtype=np.float64)
    result = decoder.predict(x)
    return LatentReadout(float(x[0]), float(x[1]), result.label, result.probabilities)


__all__ = ["LABELS", "LogisticDecoder", "decode_state", "train_decoder"]
