import numpy as np

from topology_g21.features import build_features


def test_feature_shape_and_padding():
    output = build_features(np.ones((2, 384), np.float32), np.zeros((2, 3, 384), np.float32), np.array([[1, 1, 0], [1, 1, 1]], np.float32))
    assert output.shape == (2, 1539)
