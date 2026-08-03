import numpy as np

from topology_g5.latent import equilibrium, force_for, l2


def test_equilibrium_is_additive_and_deterministic():
    first = np.array(force_for("a", 0.1)); second = np.array(force_for("b", 0.1))
    assert np.allclose(equilibrium("q", [first, second]), equilibrium("q", [first, second]))
    assert l2(equilibrium("q", [first]), equilibrium("q", [first, second])) > 0
