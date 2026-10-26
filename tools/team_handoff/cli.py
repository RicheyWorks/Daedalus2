# SPDX-License-Identifier: MIT
"""Offline checkpoint packaging and descriptive admission plans (no live work)."""
import argparse
import json
import sys

from .contracts import ContractError, plan
from .packet import read_json, read_packet, seal


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    publish = commands.add_parser("seal", help="Copy receipts and atomically publish a sealed packet")
    publish.add_argument("--store", required=True)
    publish.add_argument("--checkpoint", required=True)
    publish.add_argument("--evidence-root", required=True)
    publish.add_argument("--expected-current", required=True, help="Expected current SHA-256, or 'none' for a new store")
    for name in ("inspect", "plan"):
        command = commands.add_parser(name)
        command.add_argument("--store", required=True)
        command.add_argument("--selection", choices=("current", "previous"), default="current")
        if name == "plan":
            command.add_argument("--request", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "seal":
            packet = seal(args.store, read_json(args.checkpoint), args.evidence_root,
                          None if args.expected_current == "none" else args.expected_current)
            result = {"schema": "daedalus.takeover-publication.v1", "sha256": packet["sha256"],
                      "sequence": packet["checkpoint"]["sequence"], "published": True,
                      "live_integration_required": True, "may_execute": False}
        else:
            packet = read_packet(args.store, args.selection)
            if args.command == "plan":
                result = plan(packet["checkpoint"], read_json(args.request), packet["sha256"],
                              selection=packet["selection"])
            else:
                result = packet
        print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False))
        return 3 if result.get("status") == "held" else 0
    except (ContractError, OSError, ValueError) as exc:
        print(json.dumps({"error": {"code": getattr(exc, "code", "io_error" if isinstance(exc, OSError) else "invalid_input"),
                                   "message": str(exc)}, "may_execute": False}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
