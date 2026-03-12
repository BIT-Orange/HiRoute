"""Generate the main success-vs-overhead figure without external plotting libraries."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.simple_pdf import PdfCanvas
from tools.workflow_support import load_json_yaml, read_csv, repo_root


COLORS = {
    "exact": (0.20, 0.20, 0.20),
    "flood": (0.80, 0.27, 0.23),
    "flat_iroute": (0.95, 0.68, 0.23),
    "oracle": (0.17, 0.49, 0.36),
    "hiroute": (0.14, 0.33, 0.69),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    return parser.parse_args()


def _scale(value: float, lower: float, upper: float, out_low: float, out_high: float) -> float:
    if upper <= lower:
        return (out_low + out_high) / 2
    return out_low + (value - lower) * (out_high - out_low) / (upper - lower)


def main() -> int:
    args = parse_args()
    experiment = load_json_yaml(ROOT / args.experiment)
    rows = read_csv(repo_root() / "results" / "aggregate" / "main_success_overhead.csv")
    if not rows:
        print("ERROR: aggregate CSV is empty")
        return 1

    x_values = [float(row["mean_discovery_bytes"]) for row in rows]
    y_values = [float(row["mean_success_at_1"]) for row in rows]
    canvas = PdfCanvas()

    canvas.text(48, 368, f"{experiment['experiment_id']} success vs discovery overhead", 16)
    canvas.line(72, 72, 72, 332, 1.2)
    canvas.line(72, 72, 540, 72, 1.2)
    canvas.text(18, 332, "Success", 11)
    canvas.text(400, 36, "Mean discovery bytes", 11)

    min_x, max_x = min(x_values), max(x_values)
    min_y, max_y = 0.0, max(1.0, max(y_values))

    for tick in range(5):
        y = 72 + tick * 65
        value = _scale(tick, 0, 4, min_y, max_y)
        canvas.line(68, y, 72, y, 1.0)
        canvas.text(28, y - 4, f"{value:.2f}", 9)

    for tick in range(5):
        x = 72 + tick * 117
        value = _scale(tick, 0, 4, min_x, max_x)
        canvas.line(x, 72, x, 68, 1.0)
        canvas.text(x - 10, 52, f"{value:.0f}", 9)

    legend_y = 334
    for row in rows:
        scheme = row["scheme"]
        x = _scale(float(row["mean_discovery_bytes"]), min_x, max_x, 92, 520)
        y = _scale(float(row["mean_success_at_1"]), min_y, max_y, 92, 316)
        canvas.rect(x - 4, y - 4, 8, 8, COLORS.get(scheme, (0.3, 0.3, 0.3)))
        canvas.text(x + 8, y - 3, scheme, 10)
        canvas.rect(400, legend_y - 4, 8, 8, COLORS.get(scheme, (0.3, 0.3, 0.3)))
        canvas.text(414, legend_y - 3, scheme, 10)
        legend_y -= 18

    figure_path = repo_root() / "results" / "figures" / "fig_main_success_overhead.pdf"
    canvas.write(figure_path)
    print(str(figure_path.relative_to(repo_root())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
