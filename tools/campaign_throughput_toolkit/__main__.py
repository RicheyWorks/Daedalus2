# SPDX-License-Identifier: MIT
"""Explicit offline entry points. Outputs go only to caller-chosen new artifacts."""
import argparse
import json
from pathlib import Path
import stat
import sys

from .catalog import CatalogError, CatalogExporter
from .evidence import EvidenceError, decode
from .validation import validate_chunk
from .verification import VerificationError, verify


def load(path):
    path = Path(path)
    limit = 32 * 1024 * 1024
    if path.stat().st_size > limit:
        raise EvidenceError("control exceeds 32 MiB: " + str(path))
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise EvidenceError("control exceeds 32 MiB: " + str(path))
    return decode(raw)


def write_new(path, value):
    raw = (json.dumps(value, indent=2, allow_nan=False) + "\n").encode("utf-8")
    with Path(path).open("xb") as stream:
        stream.write(raw)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("verify", help="read-only pins/receipt check; no cadence activated")
    check.add_argument("--request", required=True)
    check.add_argument("--state", help="prior trusted local cache JSON")
    check.add_argument("--full", action="store_true")
    check.add_argument("--output", required=True, help="fresh offline report/cache directory")
    validate = commands.add_parser("validate", help="retained 20-item evidence report and proposal")
    validate.add_argument("--request", required=True)
    validate.add_argument("--report", required=True, help="fresh report JSON path")
    export = commands.add_parser("catalog", help="explicit offline chunk export")
    export.add_argument("--receipt-pin", required=True, help="JSON containing retained {path,bytes,sha256}")
    export.add_argument("--chunk", required=True, type=int)
    export.add_argument("--output-dir", required=True)
    export.add_argument("--full", action="store_true")
    export.add_argument("--trust-metadata", action="store_true", help="opt-in trusted metadata reuse")
    snapshot = commands.add_parser("snapshot", help="explicit cumulative offline stop snapshot")
    snapshot.add_argument("--output-dir", required=True)
    snapshot.add_argument("--name", default="catalog-snapshot.json")
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            request = load(args.request)
            if not isinstance(request, dict) or request.get("schema") != "daedalus-offline-verify-request/1":
                raise EvidenceError("unexpected verify request schema")
            allowed = {"schema", "pins", "roots", "chunk", "phase", "previous_chunk",
                       "previous_receipt", "previous_files", "full_every"}
            if set(request) - allowed:
                raise EvidenceError("unknown verify request fields")
            report, state = verify(request["pins"], roots=request["roots"], chunk=request["chunk"],
                                   phase=request.get("phase", "chunk"),
                                   state=load(args.state) if args.state else None, full=args.full,
                                   previous_chunk=request.get("previous_chunk"),
                                   previous_receipt=request.get("previous_receipt"),
                                   previous_files=request.get("previous_files", []),
                                   full_every=request.get("full_every", 25))
            target = Path(args.output)
            # Cache/report artifacts must never expand the verified inventory.
            if ".." in target.parts:
                raise EvidenceError("output directory must not contain parent traversal")
            for parent in (target.absolute(), *target.absolute().parents):
                if parent.exists() or parent.is_symlink():
                    info = parent.lstat()
                    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                        raise EvidenceError("output link/reparse ancestor refused")
            output = target.resolve(strict=False)
            if any(output.is_relative_to(Path(root).resolve()) for root in request["roots"]):
                raise EvidenceError("output directory must be outside evidence coverage roots")
            target.mkdir(parents=False, exist_ok=False)
            write_new(target / "report.json", report)
            write_new(target / "state.json", state)
        elif args.command == "validate":
            request = load(args.request)
            expected = {"schema", "source_manifest", "native_receipt", "roots", "chunk", "range", "item_ids"}
            if not isinstance(request, dict) or set(request) != expected or request["schema"] != "daedalus-offline-validation-request/1":
                raise EvidenceError("exact offline validation request schema required")
            report = validate_chunk(request["source_manifest"], request["native_receipt"], roots=request["roots"],
                                    expected_chunk=request["chunk"], expected_range=request["range"],
                                    expected_ids=request["item_ids"])
            write_new(args.report, report)
        elif args.command == "catalog":
            with CatalogExporter(args.output_dir, trust_metadata=args.trust_metadata) as exporter:
                report = exporter.export_chunk(load(args.receipt_pin), args.chunk, full=args.full)
        else:
            with CatalogExporter(args.output_dir) as exporter:
                report = exporter.snapshot(args.name)
        print(json.dumps(report, indent=2))
        return 0
    except (EvidenceError, VerificationError, CatalogError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"status": "refused", "native_invoked": False,
                          "native_admission": False, "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
