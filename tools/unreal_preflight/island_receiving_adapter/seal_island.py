# SPDX-License-Identifier: MIT
"""Read-only sealing tool for one natively received island (custodian-run, after the R27 native call).

Inputs are files the custodian already has; this tool never touches the editor, the broker, leases or packages:

  python seal_island.py --request request.json --queue-entry entry.json --preflight preflight.json \
      --receipt <block>/batch-complete.json --live-before before.json --live-after after.json \
      --editor-pid 60552 --out sealed.json

It re-hashes every pin named in the request from disk (so `preservation.source` is proven, not asserted), runs the
contract (`prove_destination`, `validate_preflight_shape`, `check_editor_floors`, `map_r27_receipt`,
`validate_native_result`) and writes `{candidate, sealed}` to --out, creating it exclusively (never overwrites).
Exit 0 only on a fully admitted island; 2 on any ContractError (reason on stderr, nothing written); 1 on bad input.
A held island exits 2 after writing nothing: the receipt and queue stay as the custodian left them.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import contract as c


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def rehash_request_pins(request):
    """{normalized path: sha256} for item.source, item.sidecar, protected_manifest and every recipe pin, read from disk."""
    pins = [request["item"]["source"], request["item"]["sidecar"], request["protected_manifest"]] + list(request["recipe_pins"])
    out = {}
    for pin in pins:
        p = Path(pin["path"])
        if not p.is_file():
            raise c.ContractError("pin missing on disk: " + pin["path"])
        out[str(p).replace("\\", "/")] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def seal(request, queue_entry, preflight, receipt, live_before, live_after, editor_pid, rehash=None):
    """Pure orchestration of the contract; `rehash` may be injected (tests) or computed from disk."""
    c.validate_request(request)
    if request["execution_mode"] != "native":
        raise c.ContractError("seal_island is for native requests only")
    c.prove_destination(request, queue_entry)
    c.validate_preflight_shape(request, preflight)
    c.check_editor_floors(preflight)
    if rehash is None:
        rehash = rehash_request_pins(request)
    candidate, sealed = c.map_r27_receipt(request, receipt, rehash, live_before, live_after, editor_pid)
    c.validate_native_result(request, candidate, sealed)
    return {"candidate": candidate, "sealed": sealed}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("request", "queue-entry", "preflight", "receipt", "live-before", "live-after"):
        ap.add_argument("--" + name, required=True)
    ap.add_argument("--editor-pid", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    try:
        result = seal(_load(a.request), _load(a.queue_entry), _load(a.preflight), _load(a.receipt),
                      _load(a.live_before), _load(a.live_after), a.editor_pid)
    except c.ContractError as e:
        print("REFUSED: " + str(e), file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError) as e:
        print("BAD INPUT: %s: %s" % (type(e).__name__, e), file=sys.stderr)
        return 1
    with Path(a.out).open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write("\n")
    print("SEALED %s seed=%s result_sha256=%s" % (a.out, result["sealed"]["seed"], result["sealed"]["result_sha256"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
