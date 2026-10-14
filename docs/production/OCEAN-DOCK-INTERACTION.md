# Ocean dock usable-object adapter

ADaedalusOceanDockControl derives from the existing ADaedalusUsable interface. Hero's
existing nearest-usable Interact path recognizes it without changes to Hero or
Orrery. Assign DockId, a vessel and a TravelHost actor containing a configured
UDaedalusOceanTravelComponent. Assign approved dock art through the inherited Body
component; the adapter adds no art exports or production catalog rows.

On the authority host, Use requires a valid authority hero controlling its own
pawn, the same world for all actors, a finite interaction distance within the
configured reach, and a valid host travel component. BoardAtDock then enforces
the configured dock identity, vessel realm, proximity and occupancy. Failed uses
retain hero possession. Prompt distinguishes boats, submarines, occupied vessels
and unavailable references.

This is the local/server-side boarding interaction for an already loaded realm.
Remote client interaction still needs an owning-player RPC adapter and session
permissions. It is not the Portal-to-Ocean realm transfer: the loader, destination
anchors and persistent player state still need integration. Never count a boarded
vessel as proof that a realm transition happened.

The focused test exercises Hero.Interact itself and checks actual vessel
possession, not just its boolean return (Hero currently returns true for any
nearby usable even when Use refuses). It also checks refused configuration,
distance, occupancy and restoration through the existing dock exit method.
The complete 126-file plugin compiled/reflected/linked with this adapter in a
fresh UE 5.8 host: 43 actions in 185.20 seconds, no source overlays. Both
Daedalus.Ocean.HeroDockInteraction and the existing HostEligibility test passed
with zero test errors/warnings. Exact source/DLL/log hashes and runtime report
are ocean-dock-build-proof.json and ocean-dock-runtime-proof.json. This verifies
the native interaction function path; physical E/X device dispatch, assigned art,
remote interaction and realm transfer remain acceptance gates.

The first build caught an Unreal reflected-name collision between the proposed
ADaedalusOceanDock actor and existing FDaedalusOceanDock data struct. Only the new
actor was renamed to ADaedalusOceanDockControl; the established data API remains
unchanged. Use OceanDockControl when selecting the class in Unreal/Python.
