# SPDX-License-Identifier: MIT
"""Create or inspect a frozen local World Package job; no execution command."""

import argparse
from pathlib import Path
import sys

from .batch_plan import MAX_REQUEST_BYTES, _local_path, encode_batch
from .job_store import create_job, inspect_job
from .reader_adapter import PlanError, strict_json


def main(argv=None):
    parser = argparse.ArgumentParser(description="Freeze or inspect explicit offline World Package inputs.")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("request", help="explicit v1 batch request JSON")
    create.add_argument("--output", required=True, help="fresh local job directory; existing paths are refused")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("job", help="published local job directory")
    args = parser.parse_args(argv)
    published = None
    try:
        if args.command == "create":
            source = Path(_local_path(args.request)).absolute()
            _local_path(args.output)
            with source.open("rb") as stream:
                data = stream.read(MAX_REQUEST_BYTES + 1)
            if len(data) > MAX_REQUEST_BYTES:
                raise PlanError("batch request exceeds 1 MiB")
            request = strict_json(data.decode("utf-8"))
            result = create_job(request, args.output, str(source.parent))
            published = args.output
        else:
            result = inspect_job(args.job)
        # The small CLI summary cannot fail an otherwise published job merely
        # because its complete 8 MiB plan plus manifest exceeds the plan encoder.
        print(encode_batch({"manifest": result["manifest"], "native_acceptance": False}).decode("utf-8"), end="")
    except (OSError, PlanError, UnicodeError) as error:
        suffix = "; job published at " + published + "; inspect it before retrying" if published else ""
        print("frozen job refused: " + str(error) + suffix, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
