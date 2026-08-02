import numpy as np

from micro_ltm.decode import features, train_decoder
from micro_ltm.field import energy_and_gradient, make_codebook, supports
from micro_ltm.generator import generate_split
from micro_ltm.optimize import optimize
from micro_ltm.oracle import label_for
from micro_ltm.schemas import FieldConfig


def test_oracle_and_generation_are_balanced():
    cases = generate_split("test", 12, 1729, 24, range(1, 4), True)
    assert len(cases) == 24
    assert {label_for(x) for x in cases} == {"entailed", "contradicted", "unknown"}
    assert all(label_for(x) == x.gold_label for x in cases)


def test_gradient_matches_finite_difference():
    problem = generate_split("grad", 3, 1730, 24, range(2, 3), False)[0]
    config = FieldConfig(32, 16, .01)
    codes = make_codebook(problem, config)
    state = np.random.default_rng(5).normal(size=128).astype(np.float32) * .1
    energy, grad, _ = energy_and_gradient(state, problem, codes, config)
    assert np.isfinite(energy)
    numeric = np.zeros(128)
    eps = 1e-4
    for i in range(128):
        plus, _, _ = energy_and_gradient(state + np.eye(128, dtype=np.float32)[i] * eps, problem, codes, config)
        minus, _, _ = energy_and_gradient(state - np.eye(128, dtype=np.float32)[i] * eps, problem, codes, config)
        numeric[i] = (plus - minus) / (2 * eps)
    assert np.max(np.abs(numeric - grad) / np.maximum(1e-5, np.abs(numeric))) < 2e-3


def test_optimizer_reduces_energy_and_decodes_state():
    problem = generate_split("opt", 3, 1729, 24, range(3, 4), False)[0]
    config = FieldConfig(32, 16, .01)
    result = optimize(problem, config)
    assert result.final_energy <= result.initial_energy + 1e-8
    codes = make_codebook(problem, config)
    s = supports(result.final_state, codes, config)
    assert s[0 if problem.gold_label == "entailed" else 1, problem.query_proposition] > .5


def test_decoder_has_only_two_inputs():
    x = np.asarray([[1., 0.], [0., 1.], [0., 0.]], dtype=float)
    decoder = train_decoder(x, ["entailed", "contradicted", "unknown"], epochs=20)
    assert decoder.predict(features(np.zeros(128), np.zeros((2, 24, 128)), 0)).label in {"entailed", "contradicted", "unknown"}

