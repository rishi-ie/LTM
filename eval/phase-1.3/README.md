# Phase 1.3 fixtures

`controlled-held-out.json` and `hotpotqa-300.json` are locked inputs. They are
read as data, never generated during evaluation. The controlled generator is
provided for maintainers who need to reproduce a fixture after intentionally
changing the suite; its output must be reviewed and committed before use.

The evaluator also accepts the earlier Phase 1 JSON shape, which is useful for
smoke tests but is not a Phase 1.3 result.
