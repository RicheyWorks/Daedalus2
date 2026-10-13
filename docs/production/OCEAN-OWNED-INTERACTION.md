# Owned ocean dock requests

The authority host attaches UDaedalusOceanInteractor with EnsureOnHero during
player setup, or includes it as a replicated Hero Blueprint component. It does
not modify the shared Hero class. The Hero must itself replicate for remote use.
EnsureOnHero is idempotent and refuses client actors, templates and invalid worlds.

Client OceanDockControl.Use forwards through this owned component after checking
the local controller actually possesses that Hero. The reliable RPC carries only
the dock reference. The server derives Hero from the component owner, checks its
actual authority controller/pawn/world, then calls the existing authority dock
validation. A client cannot supply another Hero as requester. Null, destroyed,
foreign-world, out-of-range, unconfigured and occupied requests refuse through
the existing checks. Session authentication and permissions remain host duties.

Dock ID, host/vessel references and interaction reach now replicate for dynamic
control points. A dynamically spawned TravelHost must replicate to be referenced
by clients; a dock can host its own server-only travel component. Request queuing
is not success: authoritative vessel possession is the result signal.

This adds remote boarding requests in an already loaded realm. Remote vessel
exit input, Portal-to-Ocean transfer, persistence and assigned art remain separate
gates. Native and actual transport verification are pending for this change.
