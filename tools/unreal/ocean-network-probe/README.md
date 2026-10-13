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
