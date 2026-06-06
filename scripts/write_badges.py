import argparse
import json
from pathlib import Path


def color_for_coverage(percent):
    if percent >= 95:
        return "brightgreen"
    if percent >= 85:
        return "green"
    if percent >= 70:
        return "yellowgreen"
    if percent >= 50:
        return "yellow"
    return "red"


def badge(label, message, color):
    return {
        "schemaVersion": 1,
        "label": label,
        "message": message,
        "color": color,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage-json", default="coverage.json")
    parser.add_argument("--test-count", type=int, required=True)
    parser.add_argument("--output-dir", default="badges")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    coverage_data = json.loads(Path(args.coverage_json).read_text())
    percent = coverage_data["totals"]["percent_covered_display"]
    percent_value = float(str(percent).rstrip("%"))

    (output_dir / "tests.json").write_text(
        json.dumps(badge("tests", str(args.test_count), "brightgreen"), indent=2) + "\n"
    )
    (output_dir / "tests-status.json").write_text(json.dumps(badge("tests", "passing", "brightgreen"), indent=2) + "\n")
    (output_dir / "autoformat.json").write_text(
        json.dumps(badge("autoformat", "passing", "brightgreen"), indent=2) + "\n"
    )
    (output_dir / "coverage.json").write_text(
        json.dumps(
            badge("coverage", f"{percent_value:g}%", color_for_coverage(percent_value)),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
