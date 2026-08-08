from __future__ import annotations

import json
import resource
import sys
import time
from pathlib import Path

from .model import Qwen, RuntimeUnavailable


def main() -> int:
    started = time.perf_counter()
    try:
        import mlx.core as mx
        import mlx_lm

        device = str(mx.default_device())
        if "gpu" not in device.lower():
            raise RuntimeUnavailable("METAL_UNAVAILABLE:default_device_not_gpu")
        model = Qwen(Path(sys.argv[1]))
        first = model.complete("Reply with exactly: ready", 8)
        second = model.complete("Reply with exactly: ready", 8)
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024)
        print(json.dumps({"status": "ready", "device": device, "mlx_version": mx.__version__, "mlx_lm_version": mlx_lm.__version__, "identical": first[0] == second[0], "first_response": first[0], "generation_ms": first[2], "load_and_smoke_seconds": time.perf_counter() - started, "peak_rss_mb": rss}))
    except RuntimeUnavailable as error:
        print(json.dumps({"status": "blocked", "reason": str(error)}))
    except (ImportError, RuntimeError) as error:
        print(json.dumps({"status": "blocked", "reason": f"METAL_UNAVAILABLE:{type(error).__name__}"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
