"""Application entry point."""

import sys


def main() -> None:
    """Launch the PyKnowledge application."""
    from .ui.app import run

    sys.exit(run())


if __name__ == "__main__":
    main()
