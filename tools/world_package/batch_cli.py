# SPDX-License-Identifier: MIT
"""Read an explicit batch request; print inventory or exclusively export a ready plan."""

import argparse
from pathlib import Path
import sys

from .batch_plan import MAX_REQUEST_BYTES, _local_path, _request, build_batch, encode_batch
from .reader_adapter import PlanError, strict_json


def main(argv=None):
    parser = argparse.ArgumentParser(description="Plan explicit World Package batches offline.")
    parser.add_argument("request", help="v1 JSON request; package paths are relative to this file")
    parser.add_argument("--output", help="create a new ready-plan JSON file; existing paths are refused")
    args = parser.parse_args(argv)
    try:
        _local_path(args.request)
        if args.output is not None:
            _local_path(args.output)
            args.output = Path(args.output)
        args.request = Path(args.request)
        with args.request.open("rb") as stream:
            data = stream.read(MAX_REQUEST_BYTES + 1)
        if len(data) > MAX_REQUEST_BYTES:
            raise PlanError("batch request exceeds 1 MiB")
        request = strict_json(data.decode("utf-8"))
        # Validate the envelope before inspecting paths, then pass a separate copy
        # so the request file and caller data stay unchanged.
        items, _ = _request(request)
        base = args.request.absolute().parent
        for item in items:
            path = Path(item["package"])
            item["package"] = str(path if path.is_absolute() else base / path)
        value = dict(request, packages=items)
        result = build_batch(value)
        encoded = encode_batch(result)
    except (PlanError, OSError, UnicodeError) as error:
        print("batch preflight refused: " + str(error), file=sys.stderr)
        return 1
    if args.output is not None and result["ready"]:
        try:
            # Exclusive create refuses existing files, links, directories and
            # input paths without truncation. Serialize fully before opening.
            with args.output.open("xb") as stream:
                if stream.write(encoded) != len(encoded):
                    raise OSError("short batch export write")
        except OSError as error:
            print("batch export failed at " + str(args.output) + ": " + str(error) +
                  "; a newly created partial file may remain", file=sys.stderr)
            return 1
    sys.stdout.write(encoded.decode("utf-8"))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
