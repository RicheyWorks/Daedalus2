#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Measure this crew's saved source output. This performs no code execution or tests.

python tools/crew/sprint_receipt.py --root . --output daedalus-server/src/main/resources/static/buckwild-sprint-receipt.json

Source lines are literal nonblank lines, including markup and comments. Data and
documentation have separate totals. Hourly pace divides by elapsed wall time,
not agent CPU time; it is an observed extrapolation, never a quality claim.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

SOURCE_SUFFIXES = {".js", ".mjs", ".html", ".css", ".py", ".java", ".h", ".cpp", ".ps1"}


def within_root(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Delivery path escapes workspace: {relative}")
    return path


def measure(root: Path, manifest: dict, now: datetime) -> dict:
    start = datetime.fromisoformat(manifest["startedAt"].replace("Z", "+00:00"))
    if start.tzinfo is None or now <= start:
        raise ValueError("The measured end must be after an explicit timezone-aware start.")
    minutes = (now - start).total_seconds() / 60
    hours = minutes / 60
    members, missing, seen = [], [], set()
    totals = {f"{kind}{field}": 0 for kind in ("source", "data", "documentation")
              for field in ("Files", "Bytes", "PhysicalLines", "NonblankLines")}
    for member in manifest["members"]:
        summary = {"member": member["member"], "realm": member["realm"], **dict.fromkeys(totals, 0), "files": []}
        for relative in member["files"]:
            path = within_root(root, relative)
            if path in seen:
                raise ValueError(f"A delivery file was attributed twice: {relative}")
            seen.add(path)
            if not path.is_file():
                missing.append({"member": member["member"], "file": relative})
                continue
            content = path.read_bytes()
            lines = content.decode("utf-8-sig").splitlines()
            category = "source" if path.suffix.lower() in SOURCE_SUFFIXES else "documentation" if path.suffix.lower() == ".md" else "data"
            row = {"path": relative, "category": category, "bytes": len(content), "physicalLines": len(lines),
                   "nonblankLines": sum(bool(line.strip()) for line in lines), "sha256": hashlib.sha256(content).hexdigest()}
            summary[category + "Files"] += 1
            for field in ("Bytes", "PhysicalLines", "NonblankLines"):
                summary[category + field] += row[field[0].lower() + field[1:]]
            summary["files"].append(row)
        summary["sourceNonblankLinesPerHour"] = round(summary["sourceNonblankLines"] / hours, 2)
        for key in totals:
            totals[key] += summary[key]
        members.append(summary)
    totals["sourceNonblankLinesPerHour"] = round(totals["sourceNonblankLines"] / hours, 2)
    return {"schemaVersion": 1, "sprint": manifest["sprint"], "startedAt": start.isoformat(), "measuredAt": now.isoformat(),
            "elapsedMinutes": round(minutes, 3), "measurementBasis": manifest["startBasis"], "baseline": manifest["baseline"],
            "lineDefinition": "Literal nonblank source-file lines, including markup and comments; data/docs separate.",
            "paceMeaning": "Observed saved-source output divided by crew elapsed wall time; extrapolated, not sustained or quality evidence.",
            "testsRun": False, "buildsRun": False, "runtimeValidated": False,
            "members": members, "totals": totals, "missingFiles": missing}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--manifest", default="tools/crew/buckwild-sprint.json")
    parser.add_argument("--output", default="daedalus-server/src/main/resources/static/buckwild-sprint-receipt.json")
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = json.loads(within_root(root, args.manifest).read_text(encoding="utf-8-sig"))
    if manifest.get("schemaVersion") != 1:
        raise ValueError("Unsupported sprint manifest schema.")
    output = within_root(root, args.output)
    if any(output == within_root(root, item) for member in manifest["members"] for item in member["files"]):
        raise ValueError("Receipt output must be excluded from its own measurement.")
    receipt = measure(root, manifest, datetime.now(timezone.utc))
    output.parent.mkdir(parents=True, exist_ok=True)
    pending = output.with_suffix(output.suffix + ".pending")
    pending.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    pending.replace(output)
    print(json.dumps({"receipt": str(output), "elapsedMinutes": receipt["elapsedMinutes"],
                      "totals": receipt["totals"], "missingFiles": receipt["missingFiles"]}, indent=2))


if __name__ == "__main__":
    main()
