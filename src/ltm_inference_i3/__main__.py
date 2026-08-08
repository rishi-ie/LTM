def run() -> int:
    from .cli import main

    return main()


raise SystemExit(run())
