# Portal browser demo v1

`build_demo.py ART_ROOT OUT_DIR --realm portal` projects existing Portal JSON and
pixel-kit exports into the existing RPG browser engine. Omitting `--realm` keeps
Prismheart as the default. This is an optional browser demo, not native acceptance.

The shared payload now supplies the canonical `realm_key` (`portal` or `prism`).
Portal adds `realm_profile` with its initial level, spawn, introduction, dialogue
and `portal.save.v1` key. Shared extension hooks must use `realm_key` to avoid
applying Prism progression or landmarks to Portal. The historical `PRISM_DEMO`
test-hook name remains available for both builds.

Portal uses its exported 256 by 224 title, Arden/Mirel/Pike at canonical level one,
starting items and gold, town/interiors, world map, encounter tables, monsters,
spells and the Old Mine's three exported floors. Combat, shops, movement, settings,
controller input and inn saving use the existing engine. No boss, reward,
inventory authority or progression service is added.

Two explicit demo design choices bridge incomplete export data without editing
canonical JSON: the existing Portal town template also represents the Village
landmark, and only the last Old Mine stair to the unexported fourth floor is
sealed in a detached copy. Earlier stairs retain their authored links. Portal
boss records are absent in these exports, so the demo enables ordinary encounters
and exploration without inventing a Warden or claiming story completion. Other
Portal dungeons, authored story progression, fishing and airship unlocks remain
outside this slice. Portal's brief generic road/mine dialogue is demo glue.

Portal and Prism saves use separate keys on the same origin. Saves include
`realm_key`; a mismatched realm is refused. Historical Prism v1 saves without that
field remain Prism saves. This is local browser journey separation, not an
authentication or save-integrity guarantee.

Run the pure projection checks without art or a browser:

```console
python tools/rpg_demo/portal_realm_test.py
```

Build both realms into distinct directories, then run one headless browser/context
against one temporary HTTP origin:

```console
python tools/rpg_demo/build_demo.py ART_ROOT OUT/portal --realm portal
python tools/rpg_demo/build_demo.py ART_ROOT OUT/prism
python tools/rpg_demo/portal_demo_test.py OUT/portal OUT/prism OUT/evidence
```

`ART_ROOT` must contain the complete authored exports, including each realm's
`title/TitleBg_1x.png` from the existing `rpg_title.py` producer. The builder's
existing `--sprites` lookup can select a realm's separately staged title background
without modifying its shared art root.

The browser test checks identity, canonical party, real town-gate and mine-stair
transitions, a canonical battle through combat menus, actual inn saves, legacy
Prism continuation and both save keys surviving a same-origin round trip. Existing
test hooks stage map entrances and one encounter; they do not establish a complete
walkthrough, hardware compatibility or native readiness. The test retains a PNG
and JSON results. Build and browser outcomes belong in the delivery receipt, not
an assumption inferred from these commands.

The fixture serves the exact built JS, JSON, images and audio through Playwright
file fulfillment at their real HTTP URLs, and disables optional external fonts.
This isolates observed localhost connection resets without substituting game data
or images. It keeps one browser context and HTTP origin across page lifecycles,
explicitly checks both identities, and compares both save values byte for byte.
It validates the browser frontend; actual HTTP hosting remains unvalidated.
