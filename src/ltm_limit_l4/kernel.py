"""Compact instantiated-proposal and remaining-cost kernel for L4."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as f

from ltm_inference_i3.dataset import expression_feature
from ltm_inference_i3.formal import expression_size
from ltm_inference_i31.kernel import SearchKernel

from .axioms import executable_axioms
from .codec import problem_from_obj, read_jsonl, step_from_obj
from .exact import enumerate_proposals


class BranchingProofKernel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.expression = nn.Sequential(nn.Linear(384, 128), nn.Tanh())
        self.schema = nn.Sequential(nn.Linear(768, 128), nn.Tanh())
        self.site = nn.Sequential(nn.Linear(4, 32), nn.Tanh())
        self.score = nn.Sequential(nn.Linear(672, 192), nn.Tanh(), nn.Linear(192, 1))
        self.value = nn.Sequential(nn.Linear(256, 128), nn.Tanh(), nn.Linear(128, 1), nn.Softplus())

    def proposal_score(
        self,
        state: torch.Tensor,
        goal: torch.Tensor,
        after: torch.Tensor,
        schema: torch.Tensor,
        site: torch.Tensor,
    ) -> torch.Tensor:
        state_code = self.expression(state)
        goal_code = self.expression(goal)
        after_code = self.expression(after)
        schema_code = self.schema(schema)
        site_code = self.site(site)
        delta = after_code - goal_code
        return self.score(
            torch.cat((state_code, goal_code, after_code, delta, schema_code, site_code), dim=-1)
        ).squeeze(-1)

    def remaining_cost(self, state: torch.Tensor, goal: torch.Tensor) -> torch.Tensor:
        return self.value(torch.cat((self.expression(state), self.expression(goal)), dim=-1)).squeeze(-1)


def parameter_count(model: nn.Module) -> int:
    return sum(item.numel() for item in model.parameters())


def schema_features() -> dict[str, np.ndarray]:
    return {
        item.axiom_id: np.concatenate((expression_feature(item.left), expression_feature(item.right))).astype(np.float32)
        for item in executable_axioms()
    }


def site_feature(path: tuple[int, ...], reverse: bool, before, after) -> np.ndarray:
    return np.asarray(
        (
            min(len(path), 16) / 16,
            (path[-1] if path else 0) / 64,
            float(reverse),
            min(expression_size(after) / max(expression_size(before), 1), 4.0) / 4,
        ),
        dtype=np.float32,
    )


def _examples(workspace: Path, maximum: int = 50_000) -> tuple[np.ndarray, ...]:
    public = {str(item["problem_id"]): problem_from_obj(item) for item in read_jsonl(workspace / "training" / "public.jsonl")}
    schemas = schema_features()
    rng = random.Random(1900)
    rows: list[tuple[np.ndarray, ...]] = []
    gold_path = workspace / "training" / "evaluator-gold.jsonl"
    for line in gold_path.open(encoding="utf-8"):
        expected = json.loads(line)
        if expected["status"] != "proved":
            continue
        problem = public[str(expected["problem_id"])]
        proof = tuple(step_from_obj(item) for item in expected["proof"])
        for index, step in enumerate(proof):
            proposals = enumerate_proposals(step.before)
            negatives = [item for item in proposals if item.after != step.after]
            if not negatives:
                continue
            negative = negatives[rng.randrange(len(negatives))]
            positive_schema = schemas[step.application.axiom_id]
            negative_schema = schemas[negative.axiom_id]
            rows.append(
                (
                    expression_feature(step.before),
                    expression_feature(problem.goal),
                    expression_feature(step.after),
                    positive_schema,
                    site_feature(step.application.site_path, step.application.reverse, step.before, step.after),
                    expression_feature(negative.after),
                    negative_schema,
                    site_feature(negative.path, negative.reverse, step.before, negative.after),
                    np.asarray(float(len(proof) - index - 1), dtype=np.float32),
                )
            )
            if len(rows) >= maximum:
                break
        if len(rows) >= maximum:
            break
    if not rows:
        raise RuntimeError("NO_TRAINING_EXAMPLES")
    columns = tuple(np.asarray([row[index] for row in rows], dtype=np.float32) for index in range(9))
    return columns


def train_kernel(workspace: Path, *, steps: int, batch_size: int, seed: int) -> tuple[BranchingProofKernel, tuple[float, ...]]:
    torch.manual_seed(seed)
    torch.set_num_threads(4)
    columns = _examples(workspace)
    model = BranchingProofKernel()
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=.01)
    rng = np.random.default_rng(seed)
    losses: list[float] = []
    for _ in range(steps):
        selected = rng.choice(len(columns[0]), size=min(batch_size, len(columns[0])), replace=False)
        state, goal, positive, positive_schema, positive_site, negative, negative_schema, negative_site, distance = (
            torch.from_numpy(column[selected]) for column in columns
        )
        positive_score = model.proposal_score(state, goal, positive, positive_schema, positive_site)
        negative_score = model.proposal_score(state, goal, negative, negative_schema, negative_site)
        ranking = f.relu(0.5 - positive_score + negative_score).mean()
        value = f.mse_loss(model.remaining_cost(positive, goal), distance)
        wrong_goal = torch.roll(goal, 1, 0)
        goal_separation = f.relu(
            0.25
            - positive_score
            + model.proposal_score(state, wrong_goal, positive, positive_schema, positive_site)
        ).mean()
        loss = 2.0 * ranking + 0.75 * value + goal_separation
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        losses.append(float(loss.detach()))
    return model.eval(), tuple(losses)


def save_kernel(path: Path, model: BranchingProofKernel, losses: tuple[float, ...], seed: int) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model": model.state_dict(), "losses": losses, "seed": seed}, path)
    return {
        "parameters": parameter_count(model),
        "weight_bytes": sum(item.numel() * item.element_size() for item in model.parameters()),
        "final_loss": losses[-1],
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def load_kernel(path: Path) -> BranchingProofKernel:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    model = BranchingProofKernel()
    model.load_state_dict(payload["model"])
    return model.eval()


def load_frozen_r13(path: Path) -> SearchKernel:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    model = SearchKernel()
    model.load_state_dict(payload["model"])
    return model.eval()
