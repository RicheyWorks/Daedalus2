# Buckwild crew source handoff — 2026-10-14

Lead: `buckwild-sol`, Codex chat `01a13bd0-4127-7dd1-b74f-7f3750012b9c`.
Integration partner: Poot Scoot (`pootscoot`, `pootscoot-coordination` on the existing team hub).

Each crew member owns a separate realm:

| Crew member | Realm | Concrete source |
| --- | --- | --- |
| buckwild-sol | Gallery City | 68-parcel city visitor, proximity surveys, maze art, three-echo memory quest, shared atlas |
| parcels_coder | Parcels | 60-plot visitor, six sequential survey objectives, plot dossiers, local journal |
| portal_coder | Portal Realm | Existing DRR 1 map reader, seeded linked exploration and local adventure journal |
| realm_audit | Shattered Planet | Ark expedition, all-realm finish outline and NFT release preparation catalog |

## Entry routes

- `/metaverse.html`: original Shattered Atlas, realm directory, release dependencies and crew output receipt.
- `/gallery-city.html?seed=7`: Gallery visitor; optional `world` selects a mounted GALLERY instance.
- `/parcels-realm.html`: district expedition; optional `world` and `seed`.
- `/portal-expedition.html?seed=7`: Portal expedition from the existing seeded DRR spec.
- `/sky-expedition.html`: Shattered Planet ark expedition and fragment survey.

All maps retain the server or shipped seed/spec identity when reading existing sources. Drafts are
labelled. Visitor progression stays on the device; it grants no server inventory, deed ownership or mint.
The new crew uses existing realm reads without writing cubes, parcels, native levels or contracts.

The public production static inventory gains exactly eighteen named GET paths for these assets, the
atlas, catalog and receipt. No API matcher, write authorization or wildcard access rule is changed.
No new dependency, package installation, editor, build or renderer is required to author this source.

## Pipeline audit and land-release scope

The finish outline is `docs/BUCKWILD-REALM-OUTLINE.md`; the machine-readable companion is
`static/realm-release-catalog.json`. They cover the established realms plus explicitly marked optional
Ocean, the Sol Portal district and the provisional Lantern proposal.

Existing live statuses are attributed to project documentation. Poot's coordinator acknowledged the
corrected allocation in hub message 30757. The existing Labyrinth and Bricks coders retain their source
claims; the Portal control-profile coder retains their native files. The shared Unreal operator and
current importer remain with their owners. The legacy island voucher and the proposed canonical
`(realm, number)` identity require reconciliation before a multi-realm land launch. Prices, launch
dates, holder allocation and deployed ownership were not invented or claimed by this sprint.

The primary checkout contained prior user edits in connector code, lessons, economy and story. Those
edits are excluded. Delivery is copied into the isolated `buckwild-realms` managed worktree at observed
`origin/main` revision `170790d0d8236e8339f3c88c0041de2d14e00099`, then committed on
`codex/buckwild-realms`. Only the listed new files and bounded static inventory addition are included.

## Measured source receipt

`tools/crew/buckwild-sprint.json` names each coder, realm and exact authored paths. Running
`python tools/crew/sprint_receipt.py` counts their saved files into
`static/buckwild-sprint-receipt.json`; it executes no application code and performs no tests.

The receipt measures elapsed wall time from the first observed clock, 2026-10-14 19:11:45 UTC
(12:11:45 p.m. Pacific). It reports source bytes, physical/nonblank source lines, separate data/doc
counts and per-member output. Nonblank lines include comments and markup. Source hourly pace is
the observed saved output divided by elapsed crew time; it is not a sustained rate or quality proof.
The generated receipt excludes itself, earlier user changes and generated asset counts.

## Acceptance remaining

No tests, build, JavaScript execution, browser playthrough, Unreal call or chain transaction occurred
in this source sprint, as requested. The work is source ready, with runtime acceptance deferred.
The current pull-request workflow runs tests, so this no-testing handoff publishes the source branch
without opening a PR. Poot receives the exact head, file list, routes and receipt for integration.
The existing build/editor/land release processes can consume this source under their normal owners.
