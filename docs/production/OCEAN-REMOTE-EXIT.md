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

Native and real transport verification are pending for this change. Realm
loading, persistent sessions, authentication/permissions, assigned art and
physical device acceptance remain separate.
