# island_receiving_adapter (R22 job 2: hephaestus PROPOSED 2026-10-27, R27-aligned by unreal-team 2026-10-29)

Typed contract and contract tests for the island production receiving adapter. Two paths:

* **mock**: the existing offline boundary (`island-continuation-source`), unchanged.
* **native**: R27's existing production receiver (`producer-full-queue-r27-speed/native_receiver.py`). The native result
  is R27's `batch-complete.json`; `validate_r27_receipt` applies the receiver's own `validate_result` rules and
  `map_r27_receipt` binds it to the request with a sealed identity receipt. See
  `docs/production/ISLAND-RECEIVING-ADAPTER-CONTRACT-PROPOSED-20261027.md` for how each of Boss's 8 OPEN answers landed.

Sole runtime custodian: `codex-play-guard` (Richey, Oct 29). Not adopted yet; no production wiring, no I/O, no editor,
broker or lease calls. `ProposedNativeAdapter` raises.

Tests (synthetic): `python -m unittest discover -s tools/unreal_preflight/island_receiving_adapter -p "test_*.py"`

## seal_island.py (custodian-run, read-only)

After the R27 native call, the custodian can seal one island without any editor, broker or lease call:

    python tools/unreal_preflight/island_receiving_adapter/seal_island.py --request request.json --queue-entry entry.json --preflight preflight.json --receipt <block>/batch-complete.json --live-before before.json --live-after after.json --editor-pid <pid> --out sealed.json

It re-hashes every request pin from disk, runs the whole contract and writes `{candidate, sealed}` exclusively (never
overwrites). Exit 0 only for a fully admitted island; 2 on any refusal (held island included) with nothing written; 1 on bad input.
