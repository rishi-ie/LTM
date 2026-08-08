# Canonical Python environment

LTM-ARCH-1.0 uses Python `3.11.x` in `.venv`. The checked lock targets macOS
Apple Silicon, the platform used for the measured local model experiments.

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements/py311-macos.lock
.venv/bin/python -m pip install -e .
```

For a minimal editable development install without historical MLX execution:

```bash
.venv/bin/python -m pip install -e ".[dev,neural]"
```

`.venv-g101` is retained only as ignored historical state. It is not a
supported verification environment. Models, workspaces and environments are
never committed.

The lock is generated from a clean Python 3.11 environment and contains no Git
URLs, local paths, editable project record or model artifact.
