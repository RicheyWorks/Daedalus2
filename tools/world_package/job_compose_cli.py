# SPDX-License-Identifier: MIT
"""Compose explicit frozen child jobs or inspect a completed composite offline."""

import argparse
import sys

from .batch_plan import encode_batch
from .job_compose import compose_jobs, inspect_composite_job
from .reader_adapter import PlanError


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compose or inspect frozen World Package jobs offline.")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("--child", nargs=2, action="append", required=True, metavar=("KEY", "JOB"))
    create.add_argument("--output", required=True, help="fresh outer directory; existing outputs refuse")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("job", help="published composite directory")
    args = parser.parse_args(argv)
    published = None
    try:
        if args.command == "create":
            result = compose_jobs([{"key": key, "job": job} for key, job in args.child], args.output)
            published = args.output
        else:
            result = inspect_composite_job(args.job)
        print(encode_batch({"manifest": result["manifest"], "native_acceptance": False}).decode("utf-8"), end="")
    except (OSError, PlanError, UnicodeError) as error:
        suffix = "; composite published at " + published + "; inspect before retrying" if published else ""
        print("job composition refused: " + str(error) + suffix, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
