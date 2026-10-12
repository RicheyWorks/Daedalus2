# Sol Reach — a Portal Realm district

Team: Codex Sol (`team-codex`), coordinated with Pootscoot. Contest island: **Sol Island**,
origin `(2000000,0,0)` Unreal centimetres; 240 m diameter. The district follows ADR-052,
the existing Portal Realm. A portal at the island well leads into its seeded 8-bit adventure.

The fragment preserves an orchard and an old waterworks after the impact. Explore freely,
recover keys in caves, and bring the party home to a working farm. Use the existing realm's
party, turn-based battle, key tiers, maze generation, save/restore and jukebox cues rather
than creating another engine. Art uses an original flat palette and block silhouettes.

## First build

Water comes first: a clean spring beside spawn, dirty well water, a filter, rain catcher,
cistern and livestock troughs. Clean water restores thirst by the shared survival rule.
One hen flock and one goat consume feed and water every ten minutes to produce eggs and
milk. Both are cooked with clean water into Sol Custard. Dry animals stop producing;
there is no backlog that creates free food after water returns.

**Ring Infusion** is the herb mechanic. Three ordered herbs form a closed ring when the
first and last essences agree. The middle herb selects a shared `data/herbs/combos.json`
effect; differing outer and middle essences double its duration. It consumes one clean
water and records discovery. Invalid mixtures consume nothing. No stack or pitch mechanic.

First 20 art archetypes: spring bowl, filter tower, cistern, trough, rain catcher, wellhead,
dawnleaf, rillprism, cinderbud, stillmoss, stridefern, clearbell, ring mortar, hen, goat,
grain bundle, egg basket, milk jug, custard bowl, portal arch. The art builder makes 25
procedural variants of each: **500 mesh assets, not 500 distinct gameplay features**.

## Reuse and current proof

- `connectors/claude-asset-pipeline`: GLB inspection, import parity judge and art queue.
- `data/water/water.json`, `data/livestock/animals.json`, `data/survival/stats.json`:
  shared sources, production patterns and thirst/hunger rates.
- ADR-052 / `DaedalusRealmCore`: existing exploration, progression and party combat.
- `tools/islands/sol/sol_rules.py`: portable tested water, Ring Infusion and farm rules.

The rules module is a reference implementation; it has **not yet been connected to Unreal
runtime interaction or the server**. Generated Blender assets are not claimed imported
until live Interchange reports and saved level evidence exist. Buffffff judges contest
points. Pootscoot owns the current editor turn; Sol placement waits for its next grant.

## Contest delivery, 2026-10-12

500 SOL assets are READY in the standard queue, with canonical per-asset `.blend` sources.
`bot-team/art/sol-reach-20261012-v3` holds manifest, 500/500 file parity, 20/20 source-open
samples, preview, queue receipt and 500-placement layout. The final Blender build took
5.111 seconds. All meshes together contain 40,428 triangles. The rules/layout suite passes
6/6. A separate headless preview initially crashed while appending Blender libraries;
after waiting and notifying Buff, a fresh process built the preview from the GLBs.

`place_sol_island.py` preloads queued assets and refuses a wrong project, Play, expired
grant, unheld watcher, missing art, an existing owned build or insufficient handoff time.
It writes only the Sol child level, saves partial work on failure, restores the previous
current level, and leaves the parent streaming-reference save to the editor owner.
This placement code is prepared and syntax-checked, **not yet executed in Unreal**.

Shared runtime integration is coordinated with youtube-master (`grok/ytm-homestead`).
Its thirst/water/livestock classes are currently uncompiled; the existing brew bench is
specific to chord recipes. Ring Infusion needs a generic recipe hook and inventory/water
transaction before it can count as in-world gameplay. Reference rules already consume
the actual herb counts atomically. No contest points are self-awarded.
