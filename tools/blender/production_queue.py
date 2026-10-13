"""Read-only export backlog report; never grants an editor turn or invents proof.

Supply validated production-data.json files and a team-maintained receipt ledger.
Receipts: [{"id": "...", "sha256": "...", "stage": "Imported|Play proven",
            "owner": "...", "evidence": "..."}].
Evidence is a reference to inspect, not automatically verified gameplay proof.
"""
import argparse
import json
from pathlib import Path


def report(batches, receipts, threshold=32):
    if threshold < 1:
        raise ValueError("Backlog threshold must be positive")
    assets = {}
    for batch in batches:
        for asset in batch:
            key = asset['id']
            digest = asset['sha256']
            if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
                raise ValueError(f"Invalid SHA256 for {key}")
            if key in assets:
                raise ValueError(f"Duplicate asset ID: {key}")
            if asset.get('export') != 'Validated':
                raise ValueError(f"Export validation missing: {key}")
            assets[key] = asset
    stages = {key: 'Exported' for key in assets}
    evidence = {}
    ranks = {'Exported': 0, 'Imported': 1, 'Play proven': 2}
    for receipt in receipts:
        key = receipt['id']
        if key not in assets:
            raise ValueError(f"Unknown receipt asset: {key}")
        if receipt.get('sha256') != assets[key]['sha256']:
            raise ValueError(f"Stale receipt: {key}")
        stage = receipt.get('stage')
        if stage not in ('Imported', 'Play proven'):
            raise ValueError(f"Invalid receipt stage: {key}")
        if not receipt.get('owner', '').strip() or not receipt.get('evidence', '').strip():
            raise ValueError(f"Receipt owner/evidence missing: {key}")
        if ranks[stage] >= ranks[stages[key]]:
            stages[key] = stage
            evidence[key] = receipt
    waiting = sorted(k for k, stage in stages.items() if stage == 'Exported')
    return {
        'validated_exports': len(assets),
        'import_receipts': sum(ranks[s] >= 1 for s in stages.values()),
        'play_proof_receipts': sum(s == 'Play proven' for s in stages.values()),
        'waiting_for_import': waiting,
        'backlog_threshold': threshold,
        'request_claude_turn': len(waiting) >= threshold,
        'editor_permission': 'Requires current team handoff; this report grants no lease',
        'work_plan': ['Code', 'Code', 'Code', 'Code', 'Blender'],
        'planned_code_share': 0.8,
        'actual_time_share': None,
        'receipts_require_human_review': list(evidence.values()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('batches', nargs='+', type=Path)
    parser.add_argument('--receipts', type=Path)
    parser.add_argument('--threshold', type=int, default=32)
    args = parser.parse_args()
    batches = [json.loads(p.read_text(encoding='utf8')) for p in args.batches]
    receipts = json.loads(args.receipts.read_text(encoding='utf8')) if args.receipts else []
    print(json.dumps(report(batches, receipts, args.threshold), indent=2))


if __name__ == '__main__':
    main()
