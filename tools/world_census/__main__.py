# SPDX-License-Identifier: MIT
"""Run with python -m tools.world_census; no network or engine dependencies."""

import argparse
import sys
from pathlib import Path

from .census import CensusError, build_census, write_reports


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Count asset definitions in explicitly supplied exported World Package JSON manifests.")
    parser.add_argument("manifests", nargs="+", type=Path, help="exported manifest.json files; no discovery or asset reads")
    parser.add_argument("--snapshot-date", required=True, help="explicit YYYY-MM-DD date for this snapshot")
    parser.add_argument("--bindings", type=Path, help="optional versioned explicit realm/asset-island bindings JSON")
    parser.add_argument("--output-dir", required=True, type=Path, help="new directory in an existing parent for census.json and daily.csv")
    args = parser.parse_args(argv)
    try:
        report = build_census(args.manifests, args.snapshot_date, args.bindings)
        outputs = write_reports(report, args.output_dir)
    except CensusError as exc:
        print(f"world-census: {exc}", file=sys.stderr)
        return 2
    print(f"{report['totals']['worlds']} worlds, {report['totals']['asset_definitions']} asset definitions; " + ", ".join(str(p) for p in outputs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
