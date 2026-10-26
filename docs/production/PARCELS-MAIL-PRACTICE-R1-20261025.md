# Parcels Street Mail Practice — edition 1, 25 October 2026

## Complete local loop

PAR01-mail-route.md explicitly asks for placed mailboxes, a seeded delivery
board, street waypoint arrows, Use-key delivery and the Ghost letter. ADR-033
defines the district. The earlier native MailRouteSession/Board deliberately
wait for canonical courier/session/district identity, trusted position/time,
day retirement, once-only settlement and persistence. Those dependencies remain.

This separate LOCAL PRACTICE course completes the walk-and-deliver lesson using
the existing portable MakeDay/Session/Waypoints rules directly. It does not bind,
alter or impersonate the canonical session. One real standalone LocalPlayer
uses the depot, walks streets, delivers seeded letters, carries the bright
Ghost envelope when present, and returns for informational practice receipts.

Base: `553e1dc3eaba25f08d97e4ad437189448f653003`.
Branch: `codex/parcels-mail-practice-20261025-r1`.
Campaign deadline: **2026-10-26 06:56:50 UTC**.

Six additive paths only:

- `Public/DaedalusMailRoutePracticeCore.h`
- `Public/DaedalusMailRoutePractice.h`
- `Private/DaedalusMailRoutePractice.cpp`
- `engines/unreal/core-test/mail_route_practice_core_test.cpp`
- `engines/unreal/core-test/run_mail_route_practice_core.cmd`
- This handoff.

Public/Private paths are under the existing DaedalusLink source module. Shared
dispatch, Hero, dialogue, inventory, Java, canonical MailRouteCore/Session/Board,
Build.cs, island production and other workers' lanes remain untouched. Previous
Bricks/Gallery/Portal packets and their identities remain preserved.

## Placement and observation contract

Place a fresh practice actor at the depot on existing flat safe ground, upright
and at unit scale; yaw is allowed. Provide the full **148m square** clear district
footprint. At 100cm per cube, Java east X maps to local Unreal X, Java north/south
Z maps to local Unreal Y, and the depot cell `(48,1,-74)` maps to the root.
Integer Java cells denote centres: inverse mapping uses
`floor(localCentimetres/100 + depotCell + .5)`, including negative coordinates.

The footprint in local centimetres is east `[-7450,7350]`, north
`[-7450,7350]`. Road strips represent four complete cube cells; their geometric
centres are half a cell west/south of the authored delivery lines. Plot borders
and the 36x36-cell plaza are only paint. All new geometry is noncolliding: this
actor creates no floor, plots, buildings, claims, teleport, helicopter or gate.
The designer/native owner must provide safe walking ground and clearance.

Only a deliberate E/X attempts setup. BeginPlay creates no mailbox, starts no
clock, binds no courier and performs no file/network I/O. One setup attempt
creates exactly the generated 6–10 regular mailboxes plus optional Ghost (up to
11), owned by this course but not attached to it. Seed, frame and exact courier
and controller are frozen. Partial setup effects are retained for review, with
no automatic retry, replacement or reset. The clock begins only after every
mailbox is ready and the courier is rechecked within two metres of the depot.

Actual local-player controller/pawn, same-world lifetime, interaction reach,
grounded CharacterMovement and capsule feet are checked for every action. Feet
must be within **25cm** of the frozen flat ground. This is a stated local-demo
tolerance, not a new canonical server-coordinate rule. Continuous horizontal
distance must also be <=200cm; quantizing 2.49 cubes to2 cannot grant extra reach.
The existing core then independently checks its cell reach and plot refusal.

Elapsed time is floored game-time difference from successful setup. Accepted
raw time is monotonic too, so `.9 -> .8` cannot hide in one integer second.
Nonfinite, backward or unrepresentable samples retain accepted clock, station,
route and receipt output. Game pause follows world game time. Authored par
assumes5 cubes/second; this actor does not change Hero movement to guarantee it.

## Player feedback and preserved rules

Mint ground arrows follow actual `Waypoints(lastSuccessfulStation,nextStop)`;
they never draw a direct diagonal through plots. Next stop follows the authored
ParOrder, but out-of-order deliveries remain legal. After a successful depot
receipt, subsequent guidance starts at the depot. Rejoin the indicated street
leg if walking elsewhere. After all stops, arrows lead home.

Numbered mailboxes distinguish STANDARD, EXPRESS with exact deadline, and GHOST
in text. Delivered labels and immediate refusal messages avoid relying on colour
alone. Depot text gives stops, last sampled clock, next mailbox and the last
receipt. The envelope is original bright two-sided geometry attached as an
owned component beside the opted-in courier after pickup, hidden after return;
no physical light, Hero material or pawn behavior is changed.

An Express letter at its deadline is on time; later letters still count as late.
Receipts can be sampled before every delivery and repeatedly afterward. They
do not end/reset/freeze the route or its clock. Ghost is excluded from ordinary
Undelivered/medal eligibility exactly as in the existing core: do not require
Ghost for Gold. Returning a picked-up Ghost changes the displayed return fact;
it does not grant an item or fly a real helicopter. The core's retained Ghost
holding flag is not rewritten; the course separately remembers its visible return.

PracticePoints is the authored receipt calculation displayed as local practice
information. No stamps, currency, inventory, companion XP, quest event, reward,
canonical save or settlement is issued. OnPracticeReceipt is explicitly
repeatable information; never wire it directly to a grant. A new practice actor
starts a separate local lesson rather than silently replacing an active round.

Lost/moved/reowned/attached mailboxes, changed seed/frame, changed courier or
unavailable displays latch refusal while retaining existing deliveries and
effects. Normal EndPlay destroys only new exact-class, exact-owned ephemeral
mailboxes and this actor's components; earlier/foreign actors stay intact.
Staged and returned spawn identities are tracked across callbacks, including
late owner assignment if the course ends during setup. No callback can reenter
and duplicate the active mutation; state commits before informational events.

## Focused evidence and native queue

Initial guarded serial MSVC C++17 /W4 /WX run: **13 groups, 0 failed**, with
10.73 GiB available physical and37.58 GiB commit headroom. It exercised negative
cell boundaries, finite/height/int limits, continuous reach, raw/floored clock,
one-time start, failure atomicity, partial/repeated receipts and one actualseed7
street tour. That generated day has no Ghost; this result is not Ghost coverage.
Two test-only groups then closed the Ghost/deadline coverage gap. One fresh
guarded run of the affected suite passed **15 groups, 0 failed**, with9.88 GiB
physical/36.78 GiB commit headroom. Bounded fixture selection found Ghost seed3
and Express seed0. Pickup/return/duplicate/repeated receipt and calculation-only
points were checked, plus distinct rounds at exact deadline versus one second
late. The core source was unchanged between runs; both logs remain preserved.

Bounded native review found and corrected one callback boundary: final setup
now repeats the two-metre depot check before starting the clock (Hero's normal
interaction reach is350cm). Existing partial mailboxes remain on refusal.
Source preflight reported **0 errors in two native paths**. The existing33/0
MailRouteCore suite is unchanged and was not rerun as practice coverage.

Native UHT/module compilation, actual walking/ground sampling, mesh/text viewing,
Ghost attachment, input/callback/streaming behavior and cooking remain
**UNCOMPILED / UNEXECUTED**. Source checks and portable simulation are not native
gameplay evidence. No editor, browser route, live staging, heavy build, push,
merge, production host adapter or reward service was used.

Minimal queued acceptance for the sole native writer:

1. Use an isolated safe148m flat fixture, unit/upright depot and normal local
   Hero. Startup creates no mailbox; first E/X creates exactly the seeded set;
   later use never duplicates/reset it. Fail setup mid-spawn and end the course
   inside a spawn callback: reconcile staged/returned effects, preserve foreign
   actors, retain partial live setup and start no clock outside two metres.
2. Walk the arrows in real time. Check all five roads, plot borders, plaza and
   mailbox labels against cells, reach, collisions/clearance and rendering.
   Deliver out of order, from a plot, too far away, above/below the ground, while
   airborne, at an Express deadline and after it; refusals keep letters.
3. Use a Ghost-containing seed, collect and inspect its carried envelope, return
   early and repeatedly, continue regular deliveries, then complete the route.
   Ghost absence must not block a regular medal; no receipt may grant anything.
   Validate game-pause clock behavior and actual movement/par assumptions.
4. Change courier/controller, seed/frame, a stop pose/owner/attachment, component
   readiness or actor lifetime during events. Refuse safely with existing facts
   retained. Confirm exact-owner teardown, repeatable event ordering and cooking.

Functional prerequisite is the earlier MailRoute core checkpoint
`8afd48495d07bf7be368179be450dc8ac9d06436` (and its existing TemperForge RNG header).
The new course does not require canonical Session/Board placement or any recent
Gallery/Bricks actor. Ancestors in bundles preserve transfer history; apply the
explicit packet and dependency, not the whole historical backlog.

## Lesson and next task

An authored deterministic rule port can support a useful local lesson without
pretending to solve multiplayer identity or settlement. State precisely what
position and clock mean, use actual street geometry for guidance, and preserve
partial work when callbacks interrupt setup. Next source priority: another
coherent non-island player feature; canonical courier identity, validated host
position/time, day lifecycle and once-only settlement/persistence remain deferred.
