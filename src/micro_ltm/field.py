from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .schemas import FieldConfig, MicroProblem, SignedLiteral


@dataclass(frozen=True, slots=True)
class EnergyBreakdown:
    facts: float
    rules: float
    conjunctions: float
    exclusion: float
    sparsity: float
    norm: float

    @property
    def total(self) -> float:
        return self.facts + self.rules + self.conjunctions + self.exclusion + self.sparsity + self.norm


def make_codebook(problem: MicroProblem, config: FieldConfig, coherence_cap: float = 0.35) -> np.ndarray:
    rng = np.random.default_rng(problem.codebook_seed)
    for _ in range(100):
        raw = rng.normal(size=(2 * config.propositions, config.dimension)).astype(np.float64)
        raw /= np.linalg.norm(raw, axis=1, keepdims=True)
        coherence = np.max(np.abs((raw @ raw.T) - np.eye(raw.shape[0])))
        if coherence < coherence_cap:
            return raw.reshape(2, config.propositions, config.dimension).astype(np.float32)
    raise RuntimeError("could not construct a sufficiently incoherent codebook")


def _index(lit: SignedLiteral) -> tuple[int, int]:
    return (0 if lit.polarity == 1 else 1, lit.proposition)


def supports(state: np.ndarray, codes: np.ndarray, config: FieldConfig) -> np.ndarray:
    logits = config.kappa * (np.einsum("d,npd->np", state, codes) - config.bias)
    logits = np.clip(logits, -60.0, 60.0)
    return 1.0 / (1.0 + np.exp(-logits))


def initial_state(problem: MicroProblem, codes: np.ndarray) -> np.ndarray:
    target = codes[0, problem.query_proposition] + codes[1, problem.query_proposition]
    return (0.05 * target).astype(np.float32)


def energy_and_gradient(
    state: np.ndarray,
    problem: MicroProblem,
    codes: np.ndarray,
    config: FieldConfig,
    include_rules: bool = True,
    undirected: bool = False,
) -> tuple[float, np.ndarray, EnergyBreakdown]:
    state64 = state.astype(np.float64, copy=False)
    codes64 = codes.astype(np.float64, copy=False)
    s = supports(state64, codes64, config).astype(np.float64)
    ds = config.kappa * s * (1.0 - s)
    grad_s = np.zeros_like(s)
    facts_energy = 0.0
    rules_energy = 0.0
    conjunction_energy = 0.0
    for fact in problem.facts:
        p, i = _index(fact)
        residual = 1.0 - s[p, i]
        facts_energy += config.fact_weight * residual * residual
        grad_s[p, i] += -2.0 * config.fact_weight * residual
    if include_rules:
        for rule in problem.rules:
            cp, ci = _index(rule.conclusion)
            if len(rule.premises) == 1:
                ap, ai = _index(rule.premises[0])
                if undirected:
                    residual = s[ap, ai] - s[cp, ci]
                    rules_energy += config.rule_weight * residual * residual
                    grad_s[ap, ai] += 2.0 * config.rule_weight * residual
                    grad_s[cp, ci] -= 2.0 * config.rule_weight * residual
                else:
                    residual = max(0.0, s[ap, ai] - s[cp, ci])
                    rules_energy += config.rule_weight * residual * residual
                    if residual:
                        grad_s[ap, ai] += 2.0 * config.rule_weight * residual
                        grad_s[cp, ci] -= 2.0 * config.rule_weight * residual
            else:
                (a, b) = rule.premises
                ap, ai = _index(a)
                bp, bi = _index(b)
                antecedent = max(0.0, s[ap, ai] + s[bp, bi] - 1.0)
                residual = max(0.0, antecedent - s[cp, ci])
                weight = 1.25 * config.rule_weight
                conjunction_energy += weight * residual * residual
                if residual:
                    if antecedent > 0.0:
                        grad_s[ap, ai] += 2.0 * weight * residual
                        grad_s[bp, bi] += 2.0 * weight * residual
                    grad_s[cp, ci] -= 2.0 * weight * residual
    exclusion_residual = np.maximum(0.0, s[0] + s[1] - 1.0)
    exclusion_energy = config.exclusion_weight * float(np.sum(exclusion_residual**2))
    grad_s[0] += 2.0 * config.exclusion_weight * exclusion_residual
    grad_s[1] += 2.0 * config.exclusion_weight * exclusion_residual
    sparsity_energy = config.sparsity_weight * float(np.sum(s * s))
    grad_s += 2.0 * config.sparsity_weight * s
    norm_energy = config.norm_weight * float(np.dot(state64, state64))
    gradient = np.einsum("np,npd,np->d", grad_s, codes64, ds)
    gradient += 2.0 * config.norm_weight * state64
    breakdown = EnergyBreakdown(
        facts_energy, rules_energy, conjunction_energy,
        exclusion_energy, sparsity_energy, norm_energy,
    )
    return breakdown.total, gradient.astype(np.float32), breakdown
