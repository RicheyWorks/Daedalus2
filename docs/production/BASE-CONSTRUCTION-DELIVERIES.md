# Reuse inventory for the first base layer

`tools/realms/construction_inventory.py` locates current deliveries for the sole editor operator.
It checks each file against the tracked production manifest and writes exact paths, SHA256s,
groups, roles and status. It never imports, starts an editor, acquires a lease or changes assets.
Missing and changed files stay distinct. Manifest paths cannot escape their delivery directory.
It reads the native session roster and WorldStyle readiness flags from source; new realms require
reconciling the inventory rather than silently disappearing from the report.

Run with `--deliveries <Documents/Codex/2026-10-13> --output <inventory.json>`.
Actual scan, 2026-10-13: all 329 inspected files exist and match the expected hashes.

| Canonical realm | Delivery folder | Manifest records | Construction use / remaining gap |
|---|---|---:|---|
| WORLD-ZERO | Existing team sublevels | Outside this manifest census | Reuse the 14 islands already laid out; inspect the current saved scene |
| GALLERY-CITY | gallery-buildout | 56 | 24 environment, 13 cast, 19 creatures; ready GALLERY generator source |
| PARCELS | parcels-buildout | 56 | 24 environment, 13 cast, 19 creatures; ready PARCELS generator source |
| BRICKS | bricks-buildout | 56 | 24 environment, 13 cast, 19 creatures; ready BRICKS generator source |
| LABYRINTH | labyrinth-full | 67 | 12 environment +12 Halloween, 13 humanoids, 22 creatures, 8 dungeon-master; WorldStyle not ready |
| PORTAL | portal-buildout | 91 | 27 environment, 16 cast, 48 monsters; Retro data, no chunk-provider entry |
| OCEAN | ocean-vessels-2 | 3 | Skiff, submarine, dock; separate optional 64-chunk host, not a full sea grid |

Folders are under the supplied delivery root. Source manifests are under `data/art/<realm>/`.
Ocean also has portable `ocean-vessels.zip` and native `ocean-native-content.zip` deliveries in
`data/art/ocean/`; the native archive includes materials, not extra independent models.

Reuse `daedalus_realm_ground.import_kit/lay`, `daedalus_plots` and `daedalus_land_grid` under
the plugin's `Content/Python`, with the operator's current source pin. Keep their deterministic
labels and per-realm folders. Do not overwrite current imported content merely because a file
exists: inspect the asset path, SHA stamp, current level, dirty packages and active jobs first.
Keep import/save batches bounded and respect RAM and editor leases.

The exact local JSON was handed to Pootscoot in hub29214. It is a file inventory, not a statement
that all assets have been imported, support collision/possession, or work in Play. Provider source
readiness does not prove a realm is mounted on a running server. The shared editor's current
actor/terrain/route inventory remains the operator's authoritative construction evidence.

Two offline regression tests cover matching, missing and changed exports plus traversal/hash
rejection. No cosmetic asset batch or duplicate terrain implementation was created by this tool.
