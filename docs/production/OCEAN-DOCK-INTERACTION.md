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
Full-plugin compile and runtime verification are pending for this new adapter.
