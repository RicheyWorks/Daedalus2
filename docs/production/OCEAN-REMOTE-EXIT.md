# Owned vessel exit requests

RequestDockExit is a reliable RPC on the possessed vessel, carrying only a dock
reference. The server derives its actual controller, requires that controller to
possess the vessel, and invokes the dock's authority exit adapter. The adapter
checks world, finite distance/reach and travel host; DisembarkAtDock then checks
the registered dock realm/radius, saved avatar identity and collision-aware exit.

The vessel's temporary Enhanced Input context maps editable InteractKey (E by
default) and the left gamepad face button (X/Square). It chooses a nearby dock;
the server independently repeats distance/configuration checks. A dock can accept
an arriving vessel other than its parked boarding vessel, provided its shared
travel host holds that player's boarding record. Null/distant/stale requests
retain vessel control. This is same-world exit, not cross-realm shore return.

The complete 128-file plugin passed all 44 build/link actions in 189.61 seconds. Both native tests passed with zero test errors/warnings, including null/distant exit rejection and restoration through the RPC wrapper. Actual localhost server/client round trips passed for boat (18.359 seconds) and submarine (18.375 seconds), including startup and handshake. Client InputKey E press/release drove the production Enhanced Input exit binding; the server verified original Hero possession, visibility and collision restored, and the client observed restored possession. Production inputs matched the committed source manifest; only the two declared probe files were added. This does not prove physical hardware input or rendered gameplay. The fixture intentionally refuses the optional HTTP service and closes its server after success, so the logs include expected connection-refused/host-closed messages. See ocean-exit-build-proof.json, ocean-exit-runtime-proof.json and ocean-exit-network-proof.json. Realm
loading, persistent sessions, authentication/permissions, assigned art and
physical device acceptance remain separate.

## Realm entry rule

Boats and submarines at docks are the player's access to the Ocean realm.
Dragon Warrior boat departures enter Ocean; returning to its land restores
Dragon Warrior. Destination docks, including underwater docks, may connect
Ocean to other registered realms. Boarding, travel and disembarking must keep
that vessel-and-dock flow visible to the player. This is the intended realm
transition contract; the same-world exit adapter above does not implement
cross-realm loading yet.
