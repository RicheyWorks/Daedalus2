# SPDX-License-Identifier: MIT
"""Offline checkpoint packaging and descriptive admission plans (no live work)."""
import argparse
import json
import sys

from .contracts import ContractError, plan
from .packet import read_json, read_packet, seal
from .source_snapshot import capture, read_snapshot
from . import operation_journal
from . import checkpoint_store
from . import source_request


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    publish = commands.add_parser("seal", help="Copy receipts and atomically publish a sealed packet")
    publish.add_argument("--store", required=True)
    publish.add_argument("--checkpoint", required=True)
    publish.add_argument("--evidence-root", required=True)
    publish.add_argument("--expected-current", required=True, help="Expected current SHA-256, or 'none' for a new store")
    snapshot = commands.add_parser("source-snapshot", help="Capture only explicitly pinned legacy receipt copies into a fresh offline store")
    snapshot.add_argument("--request", required=True)
    snapshot.add_argument("--source-root", required=True)
    snapshot.add_argument("--store", required=True)
    inspect_snapshot = commands.add_parser("inspect-source-snapshot", help="Verify the composite source capture and sealed packet")
    inspect_snapshot.add_argument("--store", required=True)
    inspect_snapshot.add_argument("--expected-receipt", help="Advertised source capture result SHA-256")
    source_request_command = commands.add_parser("source-request", help="Pin only explicitly selected retained files into an existing source request")
    source_request_command.add_argument("--selection", required=True)
    source_request_command.add_argument("--source-root", required=True)
    source_request_command.add_argument("--captured-utc", required=True, help="Explicit caller UTC declaration, never a worker START or saved event")
    checkpoint_publish = commands.add_parser("checkpoint-publish", help="Advertise a complete composite snapshot in an owned rolling index")
    checkpoint_publish.add_argument("--store", required=True)
    checkpoint_publish.add_argument("--request", required=True)
    checkpoint_publish.add_argument("--source-root", required=True)
    checkpoint_publish.add_argument("--expected-current", required=True, help="Outer composite digest, or 'none' for initialization")
    checkpoint_inspect = commands.add_parser("checkpoint-inspect", help="Verify only the advertised current or explicit previous composite")
    checkpoint_inspect.add_argument("--store", required=True)
    checkpoint_inspect.add_argument("--selection", choices=("current", "previous"), default="current")
    checkpoint_inspect.add_argument("--expected-digest", help="Trusted outer digest for the selected composite")
    journal_create = commands.add_parser("journal-create", help="Create an explicitly fresh private operation store")
    journal_create.add_argument("--store", required=True)
    journal_create.add_argument("--config", required=True)
    for name in ("journal-intent", "journal-record", "journal-cover"):
        command = commands.add_parser(name)
        command.add_argument("--store", required=True)
        command.add_argument("--request", required=True)
        command.add_argument("--evidence-root", required=True)
    for name in ("journal-inspect", "journal-recover", "journal-inventory"):
        command = commands.add_parser(name)
        command.add_argument("--store", required=True)
        if name == "journal-inventory":
            command.add_argument("--through-utc", required=True)
    for name in ("inspect", "plan"):
        command = commands.add_parser(name)
        command.add_argument("--store", required=True)
        command.add_argument("--selection", choices=("current", "previous"), default="current")
        if name == "plan":
            command.add_argument("--request", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "source-request":
            result = source_request.build_request(read_json(args.selection), args.source_root, args.captured_utc)
        elif args.command == "checkpoint-publish":
            result = checkpoint_store.publish(args.store, read_json(args.request), args.source_root,
                                              None if args.expected_current == "none" else args.expected_current)
        elif args.command == "checkpoint-inspect":
            result = checkpoint_store.read(args.store, args.selection, args.expected_digest)
        elif args.command == "journal-create":
            result = operation_journal.create(args.store, read_json(args.config))
        elif args.command in ("journal-intent", "journal-record", "journal-cover"):
            action = {"journal-intent": operation_journal.intent, "journal-record": operation_journal.record, "journal-cover": operation_journal.cover}[args.command]
            result = action(args.store, read_json(args.request), args.evidence_root)
        elif args.command == "journal-inspect":
            result = operation_journal.inspect(args.store)
        elif args.command == "journal-recover":
            result = operation_journal.recover(args.store)
        elif args.command == "journal-inventory":
            result = operation_journal.inventory(args.store, args.through_utc)
        elif args.command == "source-snapshot":
            result = capture(read_json(args.request), args.source_root, args.store)
        elif args.command == "inspect-source-snapshot":
            result = read_snapshot(args.store, args.expected_receipt)
        elif args.command == "seal":
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
