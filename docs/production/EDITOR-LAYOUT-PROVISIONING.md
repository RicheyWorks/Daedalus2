# Operator editor-layout provisioning

Stacked on PR85. This fills the missing operator import path for the existing district API and
RealmLayoutStore. It creates physical-placement candidates, never wallet/NFT/egg ownership.

`prepare_editor_layouts.py` accepts the captured editor tuple schema, preserves immutable land
numbers and current footprints, refuses duplicate JSON keys/IDs and out-of-range integer tuples,
and derives signed64-bit development seeds from an explicit namespace plus realm+land ID.
Seeds are stable across moves; they are not production mint randomness or existing terrain seeds.

`ProvisionEditorLayouts.java` reads the bounded normalized TSV and validates every realm through
RealmLayout/Estate, including district boundaries, overlap and reserved hub cells0..8. Default
mode validates without writes. --write saves revision0 snapshots in a private staging directory,
reloads and compares each one, hashes files, writes provenance, and atomically publishes the new
bundle directory. A parent writer lock serializes this tool's instances. Existing destinations
are refused; live layouts/seeds are never updated in place. Stage cleanup is flat and private.

Run from a checkout with the core classes built (Java21):
```
python tools/realms/prepare_editor_layouts.py --capture CAPTURE.json --seed-namespace DEVELOPMENT_NAMESPACE --out NEW.tsv
java --class-path daedalus-core/target/classes tools/realms/ProvisionEditorLayouts.java --input NEW.tsv
java --class-path daedalus-core/target/classes tools/realms/ProvisionEditorLayouts.java --input NEW.tsv --out NEW_BUNDLE --write
```

Actual captured input: bot-team/link/editor-lands-2026-10-13.json. Authoritative core validates
five realms/742 lands. Candidate: C:/Users/730ri/Documents/Codex/2026-10-13/editor-layout-candidate/.
Its provisioning.json contains capture hash, explicit development seed namespace and file hashes.
WORLD-ZERO102 placements (8 multi-cell estates,94 single-cell plots); other four realms160 each.
No source snapshot or editor scene modified. PR85 remains required before live HTTP consumption.

After review and PR85 integration, point daedalus.realm-layout.directory at the operator-approved
bundle and let Claude dry-run/apply the registry sync. Do not install these development seeds over
already generated terrain without reconciling the terrain seed authority. No live server restart,
registry application, ownership action, mint or engine mutation is performed by this delivery.
