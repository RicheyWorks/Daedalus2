# Parcels PAR01 mail route — source checkpoint, 2026-10-23

## Authored behavior and scope

The existing `docs/mechanics/PAR01-mail-route.md` explicitly requests native
mailboxes, a delivery board, street guidance and Use-key delivery. Its rules are
implemented in `daedalus-core/src/main/java/com/daedalus/world/parcels/MailRoute.java`,
with geometry in `world/district/DistrictOps.java` and focused Java tests in
`world/parcels/MailRouteTest.java`. Those Java sources and shared files are unchanged.

This additive source slice ports those rules and provides an explicitly configured
native board/mailbox and per-courier session projection. **It is not an
authoritative multiplayer service.** No native courier/session ownership bridge,
validated scene/position/time source, server endpoint or once-only settlement
contract exists for this mechanic in this snapshot. The default state is inactive.

## Existing-rule core

`DaedalusMailRouteCore.h` preserves the authored valid-domain rules:

- Signed Java-long seed; 6–10 ordinary letters plus at most one Ghost pickup,
  hence up to **11** solver stops. Reuse the existing tested `forge::SplitRng`
  implementation by including its header, without changing the Forge module.
- The 60 real plots, five road centre lines per axis and helipad at `(48,1,-74)`
  in Java X/Y-up/Z cube coordinates. Mailboxes remain on streets. Trespass means
  inside **any** claimable plot, regardless of its owner or claim status; no deed
  lookup or ownership operation is performed.
- Shortest street waypoints, exact Held–Karp tour and Java's strict-less-than
  tie ordering. Pace is five cubes/second; Express deadlines use the optimal
  tour arrival time, integer quarter-slack and ten seconds.
- Horizontal Euclidean reach of two cubes, deliver/pickup once, exact Express
  deadline behavior, authored stamp facts and Gold/Silver/Bronze bands.
- `Finish` samples a receipt at the helipad. It does not close the round, consume
  the Ghost flag or settle anything; later deliveries and repeated receipts stay
  legal. Ghost is excluded from ordinary undelivered-letter/medal counts.

The portable API returns refusal sentinels instead of Java exceptions for invalid
roads/plots or unrepresentable street distances. Structurally malformed days and
negative elapsed values refuse without replacing live state/output. These are
boundary guards, not claims of Java equivalence on malformed input. `Session::Start`
does not authenticate a seed; the native projection uses `MakeDay` with its explicit
host-supplied seed. No calendar-to-seed mapping is chosen.

## Native controls and binding boundary

The board derives from the existing `ADaedalusUsable` seam, so an explicitly placed
actor can receive existing E/X interaction without Hero/shared dispatch edits.
`PlotNumber = -1` denotes the helipad board; a real plot denotes a mailbox. A session
must be explicitly attached to its courier actor and explicitly assigned to each
board/mailbox. There is no global lookup, automatic component creation, placement,
network request, route start, clock sampling or inventory grant.

The depot board displays the satchel, Express deadlines, progress, numbered street
tour and an inset with directional arrows, H for helipad and numbered stops.
Completed stops also gain a `+`, so colour is not the only cue. Mailboxes show the
applicable letter or Ghost pickup and readable refusal feedback. The inset is a
canonical diagram; it does not certify that any real actor is at that location.
Elapsed values are labelled host samples rather than a locally invented countdown.

The future host adapter must supply these bindings explicitly:

1. After BeginPlay, subscribe to `OnActionRequested`, then call `ConfigureHost`
   with a live adapter object, canonical courier/session/district identities and
   day seed. The exact component owner is the bound courier. `HasHostBinding`
   remains false without a live same-world adapter, begun component/courier and
   request listener. Actor/component adapters that have ended are refused.
   Other adapter lifecycles must call `ClearHostBinding` when shutting down.
2. Place/configure boards explicitly and use `SetRouteSession` and
   `SetPlotNumber` for runtime changes. Editor properties are initial placement
   defaults; runtime reflection writes that bypass setters are unsupported.
   `ExpectedStationCube` reports the canonical expected cell only. It validates
   neither the actor transform nor a courier's real position.
3. An interaction from the exact bound courier creates one pending ticket and
   requests Start, Deliver or Receipt. The host must verify canonical ownership,
   district/seed/session identity, the station's actual scene mapping, validated
   courier position and elapsed seconds from its own round clock. Do not echo
   client-provided coordinates/time as proof. No conversion from a world FVector
   to trusted Java cells is invented here.
4. Call `CompleteHostAction` with the same live host object, ticket and explicit
   observation. Identity, seed, station/plot, canonical station cube and monotonic
   nonnegative elapsed checks fence accidental mismatches; these checks and
   `HasAuthority`/`BlueprintAuthorityOnly` are **not authentication**. The stored
   requested action/letter is used, not a replacement provided by the response.
   The ticket is consumed before mutation/result callbacks. A true return means
   the response was processed; inspect the displayed delivery outcome separately.
5. Use `RejectHostAction` when validation fails. The courier can use a station
   again to cancel an outstanding check and retry. There is no invented timeout.
   Rebind, clear, station setter changes, station/session EndPlay and teardown
   fence delayed replies. Ticket IDs are never recycled. Reentrant configuration
   changes cannot resume an older setter or bind duplicate handlers.

Unbinding retains the current round in memory. Rebinding the same keys/seed retains
its progress; replacing an active round with different keys/seed is refused. There
is no automatic new-day reset, disk save, migration or persistence claim. Round
retirement and new-day lifecycle remain part of the host contract.

All sampled receipts are explicitly **pending settlement / no rewards issued**.
They contain the authored stamp/medal facts but neither grant inventory nor issue
companion activity receipts. Repeated sampling must not become repeated awards.
The existing Java activity adapter remains owned by its existing lane.

## Exact files and evidence

Only these eight additive files belong to this checkpoint:

- `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusMailRouteCore.h`
- `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusMailRouteSession.h`
- `engines/unreal/DaedalusLink/Source/DaedalusLink/Private/DaedalusMailRouteSession.cpp`
- `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusMailRouteBoard.h`
- `engines/unreal/DaedalusLink/Source/DaedalusLink/Private/DaedalusMailRouteBoard.cpp`
- `engines/unreal/core-test/mail_route_core_test.cpp`
- `engines/unreal/core-test/run_mail_route_core.cmd`
- `docs/production/PARCELS-MAIL-ROUTE-20261023.md` (this handoff)

The actual portable header compiled once with MSVC C++17 `/W4 /WX` and passed
**33/33 checks**. A fresh guard reported **4.91 GiB free RAM** before the small
compile, above the 3 GiB minimum. Outputs stayed outside the repository. Checks
cover all 60 mailboxes, plaza exclusions, bounded street-path geometry, deterministic
days, eleven stops, one exhaustive small-route optimum, eight par tours, signed seed
extremes, deadlines/reach/duplicates, malformed-day atomic refusal, partial return,
Ghost behavior and repeated non-consuming receipts.

```text
engines\unreal\core-test\run_mail_route_core.cmd <scratch-output-directory>
```

Generated-domain correspondence to Java was reviewed in source, including RNG
draw order and solver tie order. **No cross-language Java oracle was executed.**
The standalone checks do not execute native ticket handling, UObject/component
lifetimes, usable input, text/map rendering or any server/settlement integration.
Focused source preflight/review cover the five implementation files; they are not
native UHT compilation or gameplay evidence.

All previous Portal/Gallery checkpoints are preserved, including
`57fa3d7d6dc18be81cfdba65d69abf2a05852d16` and
`fcff1f8c73c5277d378e01fb59a50029146a42a8`. The earlier 40 retention checks did
not execute the native host. No editor, live project, engine/full-repository build,
push or merge was used. No Java engine, input/dialogue, inventory, NPC, RecordHunt,
Brew/Choir, pirate/Ocean/Orrery, arcade, Prismheart, satellite or ingestion file changed.

## Ranked next steps and status

1. **Pending host contract:** the canonical courier/session owner must define the
   validated position/time and scene-coordinate bridge, day lifecycle and once-only
   settlement/persistence. This slice deliberately does not supply or bypass them.
   No production binding or awards should be activated without that contract.
2. **Pending exclusive editor release:** compile UHT/module in an isolated fixture.
   Keep default-unbound boards inactive; attach a labelled fixture host only for
   acceptance. Exercise wrong courier/host/identities/seed/station/time, duplicate
   and delayed replies, cancellation/retry, rebind away/back, same-binding reentrant
   setters, streamed board removal and component/host teardown. Verify no rejected
   action spends progress or replays a consumed ticket.
3. In that fixture, walk an actual seeded street tour, miss an Express deadline,
   attempt delivery inside a plot and outside horizontal reach, collect Ghost,
   return repeatedly, then continue remaining deliveries. Verify numbered inset,
   readable labels, pending receipts and zero inventory/settlement changes.
   Real mailbox placement, multiplayer replication, server integration, cooking
   and rendered acceptance are still unperformed.

These dependencies are **pending, not denied or attempted**. The source-only
slice is checkpointed rather than treating fixture callbacks as live authority.

## Lessons learned

Porting a deterministic quest does not establish who owns its session or prove a
position/clock. Keep that boundary visible and fail inactive without it. A Java
receipt can be sampled repeatedly; consume response tickets once without silently
turning the receipt into a once-only award or closing a still-open route.
