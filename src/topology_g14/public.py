from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path


def _download(url: str, path: Path) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "LTM-G14/1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        content = response.read()
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(content)
    return {"url": url, "path": str(path), "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}


def fetch(workspace: Path, sources: dict[str, str]) -> dict:
    output = {}
    for name, url in sources.items(): output[name] = _download(url, workspace / "benchmark-sources" / f"{name}.json")
    path = workspace / "benchmark-sources" / "manifest.json"; path.write_text(json.dumps(output, indent=2, sort_keys=True))
    return output


def count_items(path: Path, name: str) -> int:
    data = json.loads(path.read_text())
    if name == "locomo": return sum(len(item.get("qa", [])) for item in data)
    return len(data)


def split_runtime_and_gold(source_root: Path, destination: Path) -> dict:
    """Make public runtime input unable to see reference answers or evidence IDs."""
    runtime: list[dict] = []; gold: list[dict] = []
    long_data = json.loads((source_root / "longmemeval.json").read_text())
    for item in long_data:
        identifier = f"longmemeval:{item['question_id']}"
        runtime.append({"query_id": identifier, "benchmark": "longmemeval", "category": item["question_type"],
                        "prompt": item["question"], "history": item["haystack_sessions"]})
        gold.append({"query_id": identifier, "answer": item["answer"], "evidence": item["answer_session_ids"]})
    locomo_data = json.loads((source_root / "locomo.json").read_text())
    for conversation in locomo_data:
        for number, item in enumerate(conversation.get("qa", [])):
            identifier = f"locomo:{conversation['sample_id']}:{number:03d}"
            runtime.append({"query_id": identifier, "benchmark": "locomo", "category": item.get("category", "unknown"),
                            "prompt": item["question"], "history": conversation["conversation"]})
            answer = item.get("answer", item.get("adversarial_answer"))
            if answer is None:
                raise ValueError(f"LoCoMo QA item has no answer: {identifier}")
            gold.append({"query_id": identifier, "answer": answer, "evidence": item.get("evidence", [])})
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "runtime.json").write_text(json.dumps(runtime, separators=(",", ":")))
    (destination / "gold.json").write_text(json.dumps(gold, separators=(",", ":")))
    return {"runtime_cases": len(runtime), "gold_cases": len(gold), "runtime_hash": hashlib.sha256((destination / "runtime.json").read_bytes()).hexdigest(), "gold_hash": hashlib.sha256((destination / "gold.json").read_bytes()).hexdigest()}
