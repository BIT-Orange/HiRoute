"""Compatibility wrapper that renders all formal figure PDFs."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    experiment_arg = sys.argv[1:]
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/plots/plot_main_figures.py"), *experiment_arg],
        cwd=ROOT,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
