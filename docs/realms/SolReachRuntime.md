# Sol Reach native integration

The portable core is `DaedalusSolReachCore.h`. Its 32/32 native tests compile under MSVC
C++17 with `/W4 /WX` and check all 216 ordered herb combinations, atomic refusal,
overflow, progression, keeper memory, schedules and clock/weather discovery.

**Execution hold:** Richmond reported Norton alerts on the Sol Reach core test via
Pootscoot. Native test launches, build retries and Sol adapter deployment are paused
pending the actual detection/path review. The 32/32 result is the previous completed
run, not a fresh security clearance. Existing source, logs, candidate metadata and
SHA256 are preserved in the task's `security-evidence` folder. No exclusions,
quarantine restores, executable renaming or other bypasses were attempted.

`UDaedalusSolReachJournal` is the thin Unreal component. **It has not yet passed UHT,
an Unreal build or a live Play test.** No code has been copied into the running editor's
plugin. The team has been asked to include it in the existing shared compile window.

## Runtime wiring, in an approved build/turn

1. Add the journal to the Sol player's replicated actor. Server bindings deposit actual
   water, harvested herbs, eggs and milk after the existing inventory transaction succeeds.
   Shared `DaedalusHomestead` owns thirst, water-source interaction, animal timers and
   production; the journal does not add competing versions of those classes.
2. Assign the realm's existing `ADaedalusSkyDirector` to `SkyDirector`; it reads hour,
   weather and wetness. Do not spawn another world clock. Assign the secret's actual
   stair marker and proximity reach. Missing clock means no clue, and keeper stays home.
3. Bind `OnEnvironmentChanged` to marker visibility/materials and keeper AI destinations:
   dawn well, daytime garden, kitchen after a remembered meal, home at night or in storms.
   The component samples once per second and emits only on a changed result. These are
   query/event hooks; navigation and rendered shadows still need scene bindings.
4. Execute `BrewRing` on authority with three ordered herb names. It returns the effect
   and duration after atomic ledger consumption. Apply that result through the existing
   effect system. Failed inputs leave supplies, discoveries and quest facts unchanged.
   Effects are editable and their four defaults match the shared herb-combo JSON.
5. `FilterWellWater` and `CookAndShareCustard` record actual successful transactions.
   `GetAdventureStage` drives the keeper dialogue and the existing Portal Realm entry.
6. Persist `Snapshot` through the existing save service. Restore rejects wrong schema,
   malformed herb counts, negative resources and unknown fact bits. Supply
   `DeedJournalKey` only from the existing authenticated deed service. It neither mints
   nor authenticates NFTs. Snapshot replication is owner-only, keeping discoveries private.

## Visible acceptance, still pending

- Filter dirty well water and show both ledger counts change.
- Brew Dawnleaf–Rillprism–Dawnleaf: consume 2/1 herbs plus one clean water, return
  `heat_shield` for 240 seconds and show the applied effect.
- Try it again without enough Dawnleaf: refuse and preserve all counts.
- Deposit real livestock outputs, cook/share, show the keeper remember the meal and
  reach `PortalReady`; enter the existing seeded realm through its real portal.
- At the same stair: clear 06:30 reveals the clue, dry 12:00 hides it, wetness 0.7 reveals
  wet footprints. Remote discovery refuses. A repeated discovery grants no second reward.
- Save/reload the journal, retaining recipes, quest progress and keeper memory.
- End the granted editor slice with own level/assets saved, Play stopped and panels tidy.

The read-only world census confirms 500 SOL READY rows and zero imported SOL assets.
The 25 abandoned Dewroot prototypes found by that census were moved outside the art
tree, preserved under the task's retired-prototypes folder, and excluded from delivery.

## Adventure art extension

Five additional authored meshes are READY: the shadow guide stone, broken-ring mural,
hidden-cistern stair, keeper model and hearth. They have 480 triangles combined, 5/5
independent file-parity checks, 5/5 source-open checks and an inspected Blender preview.
The total queued Sol delivery is now **505 assets**. `place_sol_island.build` accepts an
optional adventure manifest; its bounded layout puts the keeper/mural by the spawn
spring and the discovery markers within Sol's island. These are art and placement
plans; the keeper mesh is not yet a navigating NPC, and the clue is not yet a rendered
shadow puzzle. Both require the event/AI bindings above and visible acceptance.

Source manifests: `bot-team/art/sol-reach-20261012-v3/manifest.json` and
`bot-team/art/sol-reach-adventure-20261012/manifest.json`. The asset builder's
`--adventure-kit` option, existing GLB witness, source verifier and queue publisher
share the same path rather than using a second art pipeline.
