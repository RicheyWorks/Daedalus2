# pin_transition

Read-only post-rebuild pin transition proposal, built on `build_receipt`. After a rebuild writes a sealed
`build-receipt.json`, this lists, per protected pins file, which pinned plugin rows would move from the old sha256
to the receipt's sha256. It changes no pins.

```
python tools/unreal_preflight/pin_transition/pin_transition.py propose --receipt <run>/build-receipt.json --pins <protected-files.json> [--pins <parity.json>] --out <your scratch>/pin-transition.json
python tools/unreal_preflight/pin_transition/pin_transition.py check --proposal <your scratch>/pin-transition.json
```

- `propose` needs the receipt's `.sha256` sidecar to match (`build_receipt.load_receipt`), reads pins rows with
  `build_receipt.load_rows` and compares them with `build_receipt.pins_diff`. The proposal records each pins file's
  path and sha256, every `from_sha256 -> to_sha256` transition, and plugin rows the receipt does not contain as
  `unresolved` (never guessed). It writes a new file plus `<proposal>.sha256` and refuses to overwrite an input, an
  existing file or write inside the plugin folder.
- `check` re-verifies the sidecar, re-hashes the receipt and every pins file and re-runs the comparison. Any moved pin,
  changed receipt or flipped byte is `STALE`.

It never edits, renames or deletes a pins file, never touches locks or leases and runs nothing. A proposal is
evidence for each pin owner's reviewed adoption, not permission to change pins. Exit 0 ok, 1 refused or stale,
2 bad input, 3 receipt invalid.