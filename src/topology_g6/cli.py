from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluate import develop, evaluate_locked, freeze, locked_suite_build, verify_run
from .report import report


def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("command",choices=("develop","freeze","locked-suite-build","evaluate","report","verify","run-all"));p.add_argument("--workspace",default="workspaces/topology-g6");p.add_argument("--offline",action="store_true");a=p.parse_args(argv);w=Path(a.workspace).resolve()
 if a.command=="develop":x=develop(w)
 elif a.command=="freeze":x=freeze(w)
 elif a.command=="locked-suite-build":x=locked_suite_build(w)
 elif a.command=="evaluate":x=evaluate_locked(w)
 elif a.command=="report":x=report(w)
 elif a.command=="verify":x=verify_run(w)
 else:
  if not (w/"development-results.json").exists():develop(w)
  if not (w/"frozen-manifest.json").exists():freeze(w)
  if not (w/"locked"/"problems.json").exists():locked_suite_build(w)
  if not (w/"locked-results.json").exists():evaluate_locked(w)
  x=report(w)
 print(json.dumps(x,indent=2,sort_keys=True));return 0
