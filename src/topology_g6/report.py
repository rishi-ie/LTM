from __future__ import annotations

import json
from pathlib import Path


def report(workspace: Path) -> dict:
    data=json.loads((workspace/"locked-results.json").read_text()); text=f"# G6 — General Typed Relation Engine Report\n\n## Classification\n\n**{data['classification']}**\n\n| Metric | Result |\n| --- | ---: |\n"+"\n".join(f"| {k.replace('_',' ')} | {v:.6g} |" for k,v in data["metrics"].items())+f"\n\nRuntime: `{data['runtime_seconds']:.3f} s`; peak RSS: `{data['peak_rss_mb']:.2f} MB`.\n\nG6 uses perfect typed topology. It does not test language compilation, latent optimization, or decoding.\n"; path=Path(__file__).resolve().parents[2]/"docs"/"g6-relation-engine-report.md"; path.write_text(text); return {"classification":data["classification"],"report":str(path)}
