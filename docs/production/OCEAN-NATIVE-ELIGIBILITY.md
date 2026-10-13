# Native ocean dock eligibility

UDaedalusOceanTravelComponent adapts the portable dock registry to Unreal.
ConfigureHost accepts the actual registered realm keys and trusted dock/connection
definitions on the authority host. Boarding positions are world-space centimetres;
radius must be finite and in (0, 10,000]. Invalid reloads preserve both prior route
data and boarding positions. This API is not a client RPC.

ADaedalusOceanVessel provides a static mesh root, replicated movement and server
travel identity for possessed boat/submarine pawns. Assign the appropriate model
and movement component in the realm integration. The pawn adds no buoyancy,
propulsion, passenger handling or submarine controls by itself.

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
