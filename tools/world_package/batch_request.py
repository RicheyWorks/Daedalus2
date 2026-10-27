# SPDX-License-Identifier: MIT
"""Build explicit batch requests without opening or discovering package archives."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from .batch_plan import MAX_ITEMS, MAX_REQUEST_BYTES, REQUEST_FORMAT, _local_path, _request
from .reader_adapter import PlanError, strict_json

MAX_RECEIPT_BYTES = 65536


def _paths(values, name, *, required=False):
    if (not isinstance(values, list) or len(values) > MAX_ITEMS or
            (required and not values)):
        raise PlanError(name + " must be an explicit array of " + ("1 to 16" if required else "at most 16") + " local paths")
    return [_local_path(value) for value in values]


def _absolute(value, base):
    path = Path(value)
    # abspath normalizes dot components without following links or accessing the
    # target. Raw text was checked before Path could normalize URL/UNC syntax.
    result = os.path.abspath(str(path if path.is_absolute() else base / path))
    return _local_path(result)


def create_request(package_paths, receipt_paths=None, *, base_directory=None):
    """Make a request using explicit paths and bounded accepted-receipt files.

    Packages are never opened/stat'ed here. Relative paths bind to the supplied
    base or current working directory, then become absolute in the output so
    saving the request elsewhere cannot redirect them. No plan is a receipt.
    """
    packages = _paths(package_paths, "packages", required=True)
    receipts = _paths([] if receipt_paths is None else receipt_paths, "receipts")
    base = Path.cwd() if base_directory is None else Path(_local_path(base_directory)).absolute()
    paths = [_absolute(value, base) for value in packages]
    if len(set(paths)) != len(paths):
        raise PlanError("the same normalized package path was selected more than once")
    request = {"format": REQUEST_FORMAT, "version": 1, "packages": [], "prior_receipts": []}
    for path in sorted(paths):
        key = "package-" + hashlib.sha256(path.encode("utf-8")).hexdigest()
        request["packages"].append({"key": key, "package": path})
    for value in receipts:
        path = Path(_absolute(value, base))
        try:
            with path.open("rb") as stream:
                data = stream.read(MAX_RECEIPT_BYTES + 1)
            if len(data) > MAX_RECEIPT_BYTES:
                raise PlanError("receipt exceeds 64 KiB")
            request["prior_receipts"].append(strict_json(data.decode("utf-8")))
        except (OSError, UnicodeError, PlanError) as error:
            raise PlanError(str(path) + ": cannot load accepted receipt: " + str(error)) from error
    _request(request)
    request["prior_receipts"].sort(key=lambda receipt: receipt["world_id"])
    encode_request(request)
    return request


def encode_request(request):
    data = (json.dumps(request, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if len(data) > MAX_REQUEST_BYTES:
        raise PlanError("batch request exceeds 1 MiB")
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description="Form an explicit offline batch request; packages are not opened.")
    parser.add_argument("packages", nargs="+", help="selected local package paths; no directories or globs are expanded")
    parser.add_argument("--prior-receipt", action="append", default=[], help="explicit accepted v1 receipt file; repeat as needed")
    parser.add_argument("--base-directory", help="base for relative paths; default is the current working directory")
    args = parser.parse_args(argv)
    try:
        result = create_request(args.packages, args.prior_receipt, base_directory=args.base_directory)
        encoded = encode_request(result)
    except (PlanError, OSError, UnicodeError) as error:
        print("batch request refused: " + str(error), file=sys.stderr)
        return 1
    sys.stdout.write(encoded.decode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
