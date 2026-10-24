"""Interactive demo: run with ``.venv/bin/python examples/spike.py``."""

from __future__ import annotations

from pycli import Cancelled, checkbox, confirm, select, textbox
from pycli.widgets import FreeText


def main() -> None:
    try:
        environment = select(
            "Deploy to?",
            ["development", "staging", "production", FreeText("Other")],
        )
        services = checkbox(
            "Services",
            ["api", "web", "worker"],
            min_selected=1,
        )
        version = textbox("Version", placeholder="0.0.0")
        if confirm(f"Deploy {version} {', '.join(services)} to {environment}?"):
            print(f"Deploying {version} {', '.join(services)} to {environment}...")
        else:
            print(f"Deployment {version} {', '.join(services)} to {environment} cancelled.")
    except Cancelled:
        print("Cancelled.")
    except KeyboardInterrupt:
        print("\nInterrupted.")


if __name__ == "__main__":
    main()
