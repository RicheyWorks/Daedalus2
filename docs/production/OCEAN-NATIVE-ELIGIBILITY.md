# Native ocean dock eligibility

UDaedalusOceanTravelComponent adapts the portable dock registry to Unreal.
ConfigureHost accepts the actual registered realm keys and trusted dock/connection
definitions on the authority host. Boarding positions are world-space centimetres;
radius must be finite and in (0, 10,000]. Invalid reloads preserve both prior route
data and boarding positions. This API is not a client RPC.

ADaedalusOceanVessel provides a box hull root with a static mesh child, replicated movement and server
travel identity for possessed boat/submarine pawns. Assign the appropriate model
and collision in the realm integration. A server-authoritative kinematic helm now
accelerates forward/reverse motion, steers yaw and lets submarines dive/surface.
Boats target the configured sea level; submarines clamp to configured maximum
depth. Movement uses swept actor offsets. This is an initial arcade controller,
not hydrodynamic buoyancy, wave following or passenger handling.

SetHelmInput is an unreliable server RPC on the possessed vessel. Unreal's actor
ownership controls which remote connection can invoke it. Inputs must be finite
and clamp to [-1,1]; unpossessed vessels cannot accept them. Commands expire after
0.5 seconds without refresh; forward speed decelerates and steering/dive stop.
The host must provide matching input mappings, collision and sea-level/depth
configuration. Tick steps cap at 0.1 seconds and refuse invalid tuning. Defaults
are 600 cm/s cruise, 300 cm/s² acceleration, 60 degrees/s yaw and 250 cm/s dive.
Client prediction and multiplayer latency behavior remain acceptance work.

Motion automation now invokes the actual RPC wrapper in an initialized standalone
game world. It verifies translation, boat height, submarine depth and stale input
stopping away from the depth boundary. The first wrapper run failed because the
synthetic world had not initialized its actors: AActor::ProcessEvent in the installed
UE 5.8 source gates dispatch on AreActorsInitialized. The test now calls
InitializeActorsForPlay and asserts that state before dispatch. The corrected
wrapper run passed; direct-handler testing was an intermediate diagnostic only.
Root mesh mobility is explicitly Movable. Standalone RPC dispatch is not remote
delivery; the subsequent two-process localhost probe below verifies that separately.
Input expiry counts full tick time even when the motion integration step is capped,
so a long frame does not extend input leases.

Two-process network verification subsequently passed for boat and submarine.
A remote test controller sent owner RPC commands for three seconds; the server
generated no helm input and observed forward motion, submarine descent and then
two seconds without movement after input expiry. Both clients completed the actual
IpNetDriver handshake. The runner stopped its owned server/client processes and
retained logs and hashes. See ocean-network-proof.json and the reproducible
tools/unreal/ocean-network-probe fixture. WAN conditions, production session
permissions and player-facing controls remain separate gates. A subsequent
three-process probe verified normal-client non-owner RPC refusal for both boats
and submarines: the foreign client logged owned=0 attempts and Unreal's explicit
owning-connection refusal while the legitimate vessel completed its motion/stop
check. See ocean-nonowner-proof.json. This tests the standard Unreal RPC API,
not malicious packet construction or account security.

ResolveForPlayer checks the component owner, controller and vessel authority,
same-world identity, actual possession in both directions, finite vessel position,
distance from the configured departure dock, current vessel realm and registered
route/vessel compatibility. Failure clears destination outputs. Success returns
the configured destination realm and arrival anchor; it does not teleport or load
a realm, update saved state, or charge inventory.

The shared host must authenticate the requesting player before invoking this API,
apply travel permissions/costs, and commit the realm transition once. Use a
server-owned vessel identity and current realm; do not populate these fields from
client request payloads. A request should contain dock IDs only. The existing
realm loader remains owned by Claude's team. No Hero/Realm files were changed.

VesselType, CurrentRealm, cruise speed, sea level and depth now replicate from
the server along with actor movement. Previously clients retained class-default
identity/configuration, even while motion replicated. Fresh two-client network
probes required client receipt of non-default server values before any input:
Ocean Realm, Boat/Submarine, 700 cm/s, 25 cm sea level and 15,000 cm depth.
Both modes then passed owner motion, input expiry and foreign-client refusal.
See ocean-replication-proof.json for exact logs and compiled input hashes.

BoardAtDock performs native possession transfer when the requesting controller
already possesses an authority avatar and both avatar and unoccupied vessel are
within the configured dock radius. The vessel must match the dock realm; surface
boats cannot board at submerged docks. Unknown docks, occupied vessels and remote
avatars are refused before possession changes. The host must additionally verify
the avatar's current realm and boarding permissions through its existing player
session; this component does not own the avatar's realm state. Preserve the old
avatar in the player session before boarding for later disembarkation. This method
adds possession, not vehicle propulsion or a completed cross-realm transition.

DisembarkAtDock restores the avatar recorded by successful boarding; callers
cannot substitute a different pawn. Both vessel and saved avatar must remain
valid authority actors in this world, the player must still possess the vessel,
and the avatar must be unoccupied. The vessel must be near a dock in its current
realm. ConfigureHost validates the dock's finite exit position within its boarding
radius. A collision-aware teleport must succeed before avatar possession changes.
Unknown docks, remote vessels and repeated exits refuse. A successful exit clears
the boarding record and allows a new boarding cycle. Records are weak references;
the host retains the avatar and owns disconnect/destruction/recovery handling.
This is same-world disembarkation. Cross-realm shore return still requires the
realm loader and persistent player session, rather than a local teleport.

## Hull and boarded-avatar collision

Movement now sweeps a query/physics-enabled Pawn-profile box root rather than
depending on collision baked into an assigned visual mesh. Default half extents
are (180,80,70) cm; fit them to the realm's vessel model in its Blueprint. The mesh
child has collision disabled to avoid duplicate body queries. This is a simple
kinematic hull, not boat damage or rigid-body water simulation.

Successful boarding records the avatar's prior collision and hidden state, then
disables collision and hides it while the vessel is controlled. Successful exit
restores those states. A refused collision-aware exit keeps the stored avatar
nonblocking; the vessel remains possessed. Native automation verified this cycle
and moved the hull against a WorldStatic box barrier: it advanced, then stopped
before hull penetration. These checks are not rendered art/nav acceptance.

## Camera and player controls

A spring-arm chase camera supplies a view behind and above the hull. Its default
arm is 650 cm with an 18-degree downward pitch and collision probe. Native camera
view checks passed; rendered composition, underwater visibility and camera clipping
still need visual acceptance with the assigned vessel art.

The vessel creates an Enhanced Input component and a temporary priority-100
mapping context. Editable keyboard defaults are W/S forward/reverse, A/D steer,
Space surface and Left Control dive. Left stick controls forward/steer; left/right
trigger axes surface/dive. Context removal runs on unpossession, controller
replication change and EndPlay, leaving the hero's context intact. The project
must use EnhancedPlayerInput, as the existing hero already expects.

SetLocalHelmInput supports local UI/joystick adapters and refuses non-local or
nonfinite input. Local input callbacks feed the same sender, capped at 20 Hz;
stale local commands clear after 0.5 seconds. The server still validates/clamps
its own input and performs all movement. Local input state is cleared when control
leaves the vessel. Boat dive input has no effect on its fixed sea-level target.

Fresh three-process tests injected press/release key events through the actual
player controller, not direct helm calls. Boat W and submarine W+Control drove
Enhanced Input actions, the local sender, owner RPC and server motion; release
stopped input, and foreign-client refusal/identity replication remained valid.
Proof is ocean-keyboard-network-proof.json. This is engine key-event dispatch,
not OS keyboard automation, rendered gameplay or physical gamepad acceptance.

Analog-event network probes also passed left-stick Y propulsion and right-trigger
dive, followed by neutral input, for both modes. They still require client identity
replication and verify foreign RPC refusal. See ocean-gamepad-network-proof.json.
Steering/surface axis combinations, mapping cleanup during real realm handoff,
physical controller hardware and rendered controls remain separate acceptance work.

## Verification

The actor/component, reflection code and automation test compiled and linked in
an isolated UE 5.8 scratch host. Daedalus.Ocean.HostEligibility then ran inside
UnrealEditor-Cmd with NullRHI and succeeded with zero errors or warnings. It
checks a possessed boat and submarine, configured output anchors, refusal of a
different controller, radius boundary and outside position, invalid vessel enum,
wrong current realm, rejected configuration preservation and unpossessed vessel.
The report is ocean-native-eligibility-proof.json. Full plugin build, multiplayer
client RPC behavior, rendered assets and live realm loading remain unverified.

Run the test after building a host containing DaedalusLink:

```text
UnrealEditor-Cmd.exe <HostProject.uproject> -NullRHI -unattended -nop4 -nosplash
  -ExecCmds="Automation RunTests Daedalus.Ocean.HostEligibility"
  -TestExit="Automation Test Queue Empty" -ReportExportPath=<report directory>
```

Inspect the report's exact test path, succeeded/failed/notRun counts and errors.
An engine exit code of zero is insufficient: the first attempt performed zero
tests because the new source directory had not been discovered. After refreshing
the scratch module rules, build output explicitly compiled the test and the
report showed one successful test. Do not count zero-test runs as acceptance.
