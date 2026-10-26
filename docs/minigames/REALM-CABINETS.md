# Realm arcade cabinets

`data/minigames/realm-arcades.json` says which realms host cabinets and how they are laid out.
`tools/minigames/realm_cabinets.py` turns it plus `docs/minigames/catalog.json` into
`data/minigames/realm-cabinets.json`: per realm, a list of cabinets with game id, host class,
local offset in metres from the realm's anchor marker (default `arcade_plaza`), yaw facing the
anchor, and a stable `StartGame` seed (crc32 of `realm:game`).

- Spec fields per realm: `realm`, `anchor`, `layout` (`row`, `grid`, `arc`), `spacing_m`, `columns`,
  `radius_m`, `include` / `exclude` (fnmatch patterns over catalog ids), `java` (Java cabinets on/off).
- Unknown game names, empty selections, duplicate realms and bad layouts fail the build.
- Realm builders resolve the anchor in their own map and spawn `ADaedalusDesktopArcade` /
  `ADaedalusJavaArcade` actors from the list. The tool makes no Unreal calls.

Edit the spec, run `python tools/minigames/realm_cabinets.py`, commit both files. CI runs `--check`
and the unit tests in `tools/minigames/test_realm_cabinets.py`.
