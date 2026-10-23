"""Interactive demo: run with ``.venv/bin/python examples/spike.py``."""

from __future__ import annotations

from pycli import Cancelled, checkbox, confirm, select


def main() -> None:
    try:
        environment = select(
            "Deploy to?",
            ["development", "staging", "production"],
        )
        services = checkbox(
            "Services",
            ["api", "web", "worker"],
            min_selected=1,
        )
        print("Selected:", services)
        if confirm(f"Deploy {', '.join(services)} to {environment}?"):
            print(f"Deploying {', '.join(services)} to {environment}...")
        else:
            print("Deploy cancelled.")
    except Cancelled:
        print("Cancelled.")
    except KeyboardInterrupt:
        print("\nInterrupted.")


if __name__ == "__main__":
    main()
