# SPDX-License-Identifier: MIT
"""Print an offline import plan; no output-file overwrite option is provided."""

import argparse
import json
from pathlib import Path
import sys

from .reader_adapter import PlanError, strict_json
from .replay_plan import build_plan


def main(argv=None):
    parser = argparse.ArgumentParser(description="Plan preservation-safe World Package destinations offline.")
    parser.add_argument("package", help="local .daedalus.zip file (URLs are not fetched)")
    parser.add_argument("--prior-receipt", type=Path, help="explicit accepted v1 receipt for this raw world ID")
    args = parser.parse_args(argv)
    try:
        prior = None
        if args.prior_receipt is not None:
            with args.prior_receipt.open("rb") as stream:
                data = stream.read(65537)
            if len(data) > 65536:
                raise PlanError("prior receipt exceeds 64 KiB")
            prior = strict_json(data.decode("utf-8"))
        result = build_plan(args.package, prior)
    except (PlanError, OSError, UnicodeError) as error:
        print("package preflight refused: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
