# Isolated ocean network probe

These test-only GameMode and Controller classes do not belong in a shipped plugin.
Copy OceanNetworkProbe.h/.cpp into the Public/Private folders of an isolated
DaedalusLink validation module containing the current ocean component/core, then
rebuild its editor host. Refresh source discovery if a newly added directory is
not compiled. No production GameMode or Hero changes are required.

Run the bundled Python runner with UnrealEditor-Cmd.exe, the scratch .uproject
and a fresh output directory as its three positional arguments. It starts a
127.0.0.1-bound server on an available UDP port, waits for its listener, then
starts a separate remote client. Each mode uses a fresh server/client pair.
The fixture controller generates helm input only on the non-authority local
client for three seconds. The server never generates helm input: it must observe
forward movement, submarine descent when selected, and two stationary seconds
after commands expire. The runner requires a client welcome/handshake record,
preserves both logs and hashes, and stops only its own subprocesses in finally.

October 13 verification: boat and submarine each passed in about 22.14 seconds.
Server boat endpoint x=1651.462 cm, z=0; submarine endpoint x=1605.789 cm,
z=-669.070 cm. Both stopped for at least two seconds. Proof is committed as
docs/production/ocean-network-proof.json; full logs remain in
Documents/Codex/2026-10-13/ocean-network-test-1. This establishes real localhost
owner RPC delivery to the server and resulting vessel motion. It does not prove
WAN behavior, non-owner refusal, client prediction, rendered appearance,
mesh collision, player-facing inputs, realm transitions or production multiplayer.

Use --non-owner for a server and two clients per mode. The second client attempts
reverse/turn/dive RPCs on a vessel it does not own, every 0.2 seconds. The runner
requires its handshake, an attempt marker with owned=0, and Unreal's explicit
"No owning connection" refusal. The server must still see the legitimate owner's
movement followed by two stationary seconds while foreign attempts continue.
Both boat and submarine passed October 13; proof is ocean-nonowner-proof.json,
full logs Documents/Codex/2026-10-13/ocean-network-nonowner-1. This verifies
non-owner refusal through Unreal's normal client RPC API. It does not emulate
forged network packets or establish production authentication/session security.

The current fixture also sets non-default server-only vessel identity/configuration:
Ocean Realm, Boat/Submarine type, cruise 700 cm/s, sea level 25 cm and depth
15,000 cm. Owner clients wait for all five replicated values and log their receipt
before generating input. The runner requires that identity marker, preventing
default values or client-side configuration from masquerading as replication.
The updated three-process runs passed both modes; latest proof is
docs/production/ocean-replication-proof.json, logs in
Documents/Codex/2026-10-13/ocean-network-identity-1. Earlier proof files retain
their original tested source hashes and results.

With --keyboard, the owner controller injects W press/release (plus Left Control
for submarine dive) via Unreal's InputKey event API. This branch never sets helm
axes directly. Both modes passed the full Enhanced Input-to-local-sender-to-RPC
path with foreign attempts continuing. Configure EnhancedPlayerInput in the
scratch host's DefaultInput.ini; it is also required by the existing hero.
Latest key-event proof is docs/production/ocean-keyboard-network-proof.json,
logs Documents/Codex/2026-10-13/ocean-network-key-input-1. Physical device and
rendered UI tests remain separate.

With --gamepad, the controller injects continuous left-stick Y axis events and
right-trigger axis events for submarine dive, then neutral values. This path also
avoids direct helm setters and passed both modes over actual transport while
foreign-client attempts continued. Proof is ocean-gamepad-network-proof.json;
logs Documents/Codex/2026-10-13/ocean-network-gamepad-1. These are engine analog
events, not physical hardware input. --keyboard and --gamepad are mutually exclusive.
