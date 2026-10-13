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
gates.

Verification: the complete 128-file plugin passed UE 5.8 UHT/compile/DLL link,
44 actions in 187.98 seconds, without production source overlays. Both existing
native ocean tests passed with the owned endpoint, including idempotent attachment,
null-request refusal and actual validated possession. The production DLL was
preserved before adding the two declared network fixture files.

Two-process localhost tests then passed for boat and submarine. The remote
controller invoked Hero.Interact; the replicated owned component sent the dock
request, the server verified vessel possession plus saved-avatar hidden/collision
state, and the client observed possession with the expected vessel type/realm.
The scenarios took 17.625 and 17.610 seconds including engine startup/handshake.
All 128 production files still matched their recorded hashes; only declared
test fixture classes were added. See ocean-owned-build-proof.json,
ocean-owned-runtime-proof.json and ocean-owned-network-proof.json.

The fixture freezes its synthetic Hero in place to isolate interaction and sends
optional foe-rule GETs to an unused loopback port. This proves the remote function
path, not hardware E/X dispatch, walking, account/session authentication,
cross-player component misuse, visual art or realm transfer.
