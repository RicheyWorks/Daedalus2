# Ocean inventory catalog

The realm-session table already names `ocean` as the Ocean catalog. The shared
inventory directory and Java loader previously contained only five catalogs,
so an authenticated Ocean catalog request returned 404. This change adds the
missing shared `ocean.dic` and loads it through `InventoryCatalogService`.

The same tab interaction serves six Ocean tabs: All, Navigation, Diving,
Salvage, Vessel and Quests. Thirteen definitions cover a tide compass, dock
chart, sonar log, dive mask, air canister, dive lantern, salvage claw, sea glass,
wreck plate, hull patch, mooring line, beacon lens and sealed courier case.
The native theme table gains the missing `ocean` style using existing rendering
controls: navy panels, teal ink and brass selection. No Slate widget or Hero
logic is replaced.

Definitions expose only INSPECT. This does not grant items or transfer bags
between realms. Repair, oxygen, sonar recording, pickup, crafting, equipping
and quest rewards need authoritative handlers before their actions are enabled.
The DIC comments and this record carry implementation status; player-facing
descriptions remain in-world prose.

## Story and mechanics proposals

The damaged beacon is the opening Ocean thread. A harbor courier identifies
the missing lens, a diver marks a wreck on the dock chart, and a shipwright
offers a repair commission. Finding the lens should require exploration rather
than a purchase. Later deliveries connect the realm docks while retaining the
established rule: board a boat to enter Ocean, return ashore to the departure
realm, and use submarine airlocks for configured cross-realm routes.

These are proposals for the existing quest and dock systems, not newly verified
quests. A handoff must bind actual pickup evidence to rewards once, handle
disconnect/retry, and preserve server-owned item counts. Air-canister effects
must follow the survival mechanic actually selected; this catalog supplies no
breathing exemption. Salvage should avoid damaging friendly reef creatures.

## Verification

- All 48 native inventory checks pass under MSVC C++17 `/W4 /WX`, including
  Ocean tab navigation, inspection intent and unchanged host-owned quantities.
- Existing Java and C++ dump adapters agree byte-for-byte for all six catalogs.
  Both reject the four corrupted fixtures.
- Six focused Java parser/service tests pass. The executable server JAR contains
  all six source catalogs byte-for-byte. The packaged production-profile smoke
  verifies authenticated HTTP 200 for each, anonymous refusal and missing 404.
- The smoke now gives its world host an explicit output-directory world file,
  preventing accidental access to developer world saves.

`ocean-inventory-packaged-proof.json` records the JAR/catalog hashes and HTTP
results. This is local packaged HTTP and native-model evidence. Live Unreal
panel rendering, player bags, world pickups and item effects remain pending
consumer acceptance. Existing catalogs and their item definitions are unchanged.
