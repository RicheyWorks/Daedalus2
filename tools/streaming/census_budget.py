# SPDX-License-Identifier: MIT
"""Census Budget Beacons (G206, disk-saver): island streaming budget planner follow-up.

Reads a World Census report (tools/world_census, format daedalus-world-census v1) and
prices every island with the DSB 1 cost ESTIMATE from tools/streaming/dsb_manifest.py
(RAM 16 MiB + 24 KiB per asset definition, disk 4 MiB + 96 KiB per asset definition).
It flags islands whose RAM or disk cost breaks the resident-set budget and lights a
beacon (green / amber / red) the game can show on each island's lighthouse.

Read-only over the census output and over data/islands/disk-saver/census-budget-v1.json.
Integers only, stdlib only, deterministic bytes. It never edits the census, the DSB
manifest or the G39 Byte Spring quota.

  python tools/streaming/census_budget.py CENSUS.json [--config CFG.json] [-o REPORT.json] [--strict]

Exit 0 = report printed/written, 1 = --strict and at least one red beacon, 2 = refusal.
"""
import argparse
import hashlib
import json
import os
import sys

# Mirrors dsb_manifest.py (BASE_*/PER_PLACEMENT_*); census_budget_test.py pins them equal.
BASE_RAM_KIB = 16384
PER_ASSET_RAM_KIB = 24
BASE_DISK_KIB = 4096
PER_ASSET_DISK_KIB = 96
MAX_KIB = 100_000_000
FORMAT = "daedalus-census-budget"
ORACLE_LIMIT = 16

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DEFAULT_CONFIG = os.path.join(ROOT, "data", "islands", "disk-saver", "census-budget-v1.json")


class CensusBudgetError(ValueError):
    pass


def _count(v, what):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise CensusBudgetError(f"{what}: expected a nonnegative integer")
    return v


def island_cost(asset_definitions):
    """(ram_kib, disk_kib) for an island with n asset definitions."""
    n = _count(asset_definitions, "asset_definitions")
    return BASE_RAM_KIB + n * PER_ASSET_RAM_KIB, BASE_DISK_KIB + n * PER_ASSET_DISK_KIB


def load_budget(cfg):
    b = cfg.get("budget") if isinstance(cfg, dict) else None
    if not isinstance(b, dict):
        raise CensusBudgetError("config: missing budget object")
    ram = _count(b.get("ram_budget_kib"), "ram_budget_kib")
    disk = _count(b.get("disk_budget_kib"), "disk_budget_kib")
    warn = _count(b.get("warn_permille"), "warn_permille")
    if not (1 <= ram <= MAX_KIB and 1 <= disk <= MAX_KIB):
        raise CensusBudgetError("budget: kib out of range")
    if not 1 <= warn <= 1000:
        raise CensusBudgetError("budget: warn_permille must be 1..1000")
    return ram, disk, warn


def read_census(doc):
    """Validate the fields we consume; return [(world_id, [(slot, asset_definitions)])] sorted."""
    if not isinstance(doc, dict) or doc.get("format") != "daedalus-world-census":
        raise CensusBudgetError("census: format must be daedalus-world-census")
    if doc.get("version") != 1 or isinstance(doc.get("version"), bool):
        raise CensusBudgetError("census: unsupported version")
    if doc.get("count_semantics") != "asset-definitions":
        raise CensusBudgetError("census: count_semantics must be asset-definitions")
    worlds = doc.get("worlds")
    if not isinstance(worlds, list) or not worlds:
        raise CensusBudgetError("census: worlds must be a nonempty list")
    out, seen = [], set()
    for w in worlds:
        wid = w.get("id") if isinstance(w, dict) else None
        if not isinstance(wid, str) or not wid.strip():
            raise CensusBudgetError("census: world id missing")
        if wid in seen:
            raise CensusBudgetError(f"census: duplicate world {wid}")
        seen.add(wid)
        isl = w.get("islands")
        if not isinstance(isl, list):
            raise CensusBudgetError(f"census: world {wid} islands must be a list")
        slots, rows = set(), []
        for i in isl:
            if not isinstance(i, dict):
                raise CensusBudgetError(f"census: world {wid} bad island")
            s = _count(i.get("slot"), f"world {wid} slot")
            n = _count(i.get("asset_definitions"), f"world {wid} slot {s} asset_definitions")
            if s in slots:
                raise CensusBudgetError(f"census: world {wid} duplicate slot {s}")
            slots.add(s)
            rows.append((s, n))
        out.append((wid, sorted(rows)))
    return sorted(out)


def max_resident(rams, budget):
    """Most islands resident at once under the RAM budget: lightest first is optimal for a count."""
    total = count = 0
    for r in sorted(rams):
        if total + r > budget:
            break
        total += r
        count += 1
    return count


def max_resident_oracle(rams, budget):
    """Brute force over every subset (tests only, n <= ORACLE_LIMIT)."""
    n = len(rams)
    if n > ORACLE_LIMIT:
        raise CensusBudgetError("oracle: too many islands")
    best = 0
    for mask in range(1 << n):
        picked = [rams[i] for i in range(n) if mask >> i & 1]
        if sum(picked) <= budget:
            best = max(best, len(picked))
    return best


def beacon(ram, disk, ram_budget, disk_budget, warn):
    flags = []
    if ram > ram_budget:
        flags.append("ram_over")
    if disk > disk_budget:
        flags.append("disk_over")
    if not flags:
        if ram * 1000 > ram_budget * warn:
            flags.append("ram_near")
        if disk * 1000 > disk_budget * warn:
            flags.append("disk_near")
    color = "red" if any(f.endswith("_over") for f in flags) else ("amber" if flags else "green")
    return flags, color


def plan(census_doc, cfg):
    ram_budget, disk_budget, warn = load_budget(cfg)
    worlds = []
    summary = {"worlds": 0, "islands": 0, "green": 0, "amber": 0, "red": 0, "worlds_spilling": 0}
    for wid, rows in read_census(census_doc):
        islands, rams = [], []
        tr = td = 0
        for slot, n in rows:
            ram, disk = island_cost(n)
            flags, color = beacon(ram, disk, ram_budget, disk_budget, warn)
            islands.append({"slot": slot, "asset_definitions": n, "ram_kib": ram, "disk_kib": disk,
                            "flags": flags, "beacon": color})
            summary[color] += 1
            rams.append(ram)
            tr += ram
            td += disk
        fits = tr <= ram_budget and td <= disk_budget
        summary["worlds"] += 1
        summary["islands"] += len(islands)
        summary["worlds_spilling"] += 0 if fits else 1
        worlds.append({"id": wid, "islands": islands, "total_ram_kib": tr, "total_disk_kib": td,
                       "fits_all_resident": fits, "max_resident": max_resident(rams, ram_budget)})
    return {
        "format": FORMAT, "version": 1,
        "snapshot_date": census_doc.get("snapshot_date"),
        "census_sources": sorted(s.get("sha256") for s in census_doc.get("sources", []) if isinstance(s, dict)),
        "cost_model": {"base_ram_kib": BASE_RAM_KIB, "per_asset_ram_kib": PER_ASSET_RAM_KIB,
                       "base_disk_kib": BASE_DISK_KIB, "per_asset_disk_kib": PER_ASSET_DISK_KIB,
                       "kind": "ESTIMATE (dsb_manifest placement model, asset definitions as placements)"},
        "budget": {"ram_budget_kib": ram_budget, "disk_budget_kib": disk_budget, "warn_permille": warn},
        "summary": summary,
        "worlds": worlds,
    }


def dumps(report):
    return json.dumps(report, sort_keys=True, indent=2) + "\n"


def _load_json(path):
    try:
        with open(path, "rb") as f:
            raw = f.read(4 * 1024 * 1024 + 1)
    except OSError as e:
        raise CensusBudgetError(f"{path}: {e.strerror}")
    if len(raw) > 4 * 1024 * 1024:
        raise CensusBudgetError(f"{path}: larger than 4 MiB")
    try:
        return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise CensusBudgetError(f"{path}: not JSON ({e})")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Flag census islands whose RAM/disk cost breaks the resident-set budget.")
    ap.add_argument("census")
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    ap.add_argument("-o", "--output", help="new report file (never overwritten)")
    ap.add_argument("--strict", action="store_true", help="exit 1 when any island is red")
    a = ap.parse_args(argv)
    try:
        census, _ = _load_json(a.census)
        cfg, _ = _load_json(a.config)
        report = plan(census, cfg)
        text = dumps(report)
        if a.output:
            try:
                with open(a.output, "x", encoding="utf-8", newline="\n") as f:
                    f.write(text)
            except OSError as e:
                raise CensusBudgetError(f"{a.output}: {e.strerror}")
    except CensusBudgetError as e:
        print(f"census_budget: refused: {e}", file=sys.stderr)
        return 2
    s = report["summary"]
    print(f"{s['islands']} islands in {s['worlds']} worlds: {s['green']} green, {s['amber']} amber, {s['red']} red; "
          f"{s['worlds_spilling']} worlds cannot hold every island resident")
    if not a.output:
        sys.stdout.write(text)
    return 1 if a.strict and s["red"] else 0


if __name__ == "__main__":
    sys.exit(main())
