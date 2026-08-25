"""Module entry point for ``python -m auto_io``."""


def main() -> None:
    try:
        from .app import run
    except ImportError as exc:
        raise SystemExit(
            "AutoIO could not start. Install dependencies with "
            "'python -m pip install -e .' and try again.\n"
            f"Details: {exc}"
        ) from exc
    run()


if __name__ == "__main__":
    main()
