# BRICKS: Stud Relay

Status: **UNVALIDATED, source-only; default-off REST extension.** No tests, builds,
services, native installation, UI changes or editor work were performed for this sprint.
Future actual integration and use are required before gameplay acceptance.

The existing eighteen-brick obby gains an optional pickup-and-checkpoint practice
challenge. A player carries two studs through each six-platform leg, banks them
on its checkpoint, and reaches the existing gold trophy with six banked studs.
Falling costs the studs carried since the last checkpoint. Completion gives
practice feedback; a fall-free completion displays a Clean Circuit ribbon.

## Established identity and source finding

Read before implementation: the existing local `docs/STORY.md` draft, repository
[realm guide](../REALMS.md), [ADR-034](../adr/ADR-034-bricks-world.md),
[world architecture](../DAEDALUS_WORLD_ARCHITECTURE.md), World One architecture,
and the pinned team plan, component registry, lessons and MESSAGES README.

BRICKS already has a studded baseplate, bright floating platforms above lava,
spawn, three checkpoints, a gold trophy finish, and a plane on a protected runway.
Sky gates remain a flight away. `BricksOps` supplies the seeded course and
`GET /api/v1/world/{id}/obby` publishes its geometry. `realm.js` holds the existing
browser progress/death/time loop. No matching backend relay state was found.

ADR-034 explicitly holds ranked best times for an identity/anti-cheat design.
This extension stays practice-only: reported landings are not verified physics,
and ribbons do not enter an inventory, reward ledger, leaderboard or economy.

## Invented design choices

These mechanics and names are original additions for this sprint, not previously
established canon or a claim that the native realm already implements them.

- **Stud Relay:** three six-platform legs using the current course. Each leg
  puts two non-solid pickups on two different non-checkpoint platforms. Their
  ids, platform indexes and corner coordinates follow the world's seed through
  a separate random stream; the original course generation does not change.
- **Footwork:** a landing reports the cube occupied by the avatar's feet.
  The player can move across the current platform to collect its corner stud.
  Advancing from a pickup platform before collecting it returns `STUD_REQUIRED`.
  Forward progress follows every platform in order; skipping returns `OUT_OF_ORDER`.
- **Checkpoint banks:** platforms 5, 11 and 17 use the existing checkpoint flags
  and standing positions. The bank saves the studs already collected. Falling
  clears only the current pocket and resumes progress from the last bank.
- **Finish feedback:** the original finish accepts a run after platform 17 and
  all six studs are banked. `BEACON_CARRIER` marks completion;
  `CLEAN_CIRCUIT` marks completion with zero reported falls. These are labels
  for this practice session. Restart clears the run and preserves revision order.
- **Readable guidance:** every pickup has a numbered id, leg, platform index,
  feet coordinate and brick color; clients can give textual/spatial guidance
  alongside color. `nextStud` and the banked/pocket lists support a HUD without
  requiring a new inventory category or shared UI implementation.

The intended presentation is a bright plastic-stud relay through the familiar
obby, ending at its trophy before the player returns to the plane and rainbow
travel. This sprint creates the rules and optional adapter; it creates no art.

## Source seams

| File | Responsibility |
|---|---|
| `daedalus-core/.../world/bricks/BricksRelay.java` | Framework-free seeded metadata and immutable state transitions |
| `daedalus-server/.../service/BricksRelayService.java` | Existing WorldHub lookup, private bounded practice runs, revisions and retry receipts |
| `daedalus-server/.../controller/BricksRelayController.java` | Separate conditional REST namespace using existing identity helper and rate limits |

The pure core can be embedded by an existing host without the REST adapter.
It reads `BricksOps.Plan`, retains only platform/finish/pickup metadata, and
returns a respawn target; it never places cubes or moves an avatar.

The adapter and controller both require the explicit property
`daedalus.bricks.relay.enabled=true`. The property is absent from existing
configuration, so the extension remains off. This document does not activate it.
Existing world, obby, client, harness, importer, transport, native and security
files remain untouched.

## REST contract for a future consumer

Version: `bricks-stud-relay/v1`. Base path:
`/api/v1/world/{worldId}/bricks-relay/v1`.

| Method and suffix | Response |
|---|---|
| `POST /runs` | 201 `OPENED`, private run snapshot and full immutable course metadata; 429 `CAPACITY` |
| `GET /runs/{runId}` | Current snapshot with revision, progress, elapsed practice time, respawn, next pickup, pocket/bank ids, ribbon |
| `POST /runs/{runId}/commands` | Command receipt and snapshot; 409 for revision or command-id conflict |
| `DELETE /runs/{runId}` | 204 releases the run slot |

All four routes require the existing verified `Authentication` subject, including
when the development profile permits API requests. They reuse
`SessionController.ownerOf`, `sessionOpen` and `sessionMove`; existing production
JWT routing is unchanged. World ids must name an existing BRICKS world. Run
reads/writes/close require the opening subject and exact world id. Another
subject's run, an absent run, and an expired run return the same 404.

Commands require `commandId` (UUID), `expectedRevision` (nonnegative integer),
and `action` (`LAND`, `FALL`, `FINISH`, `RESTART`). `LAND` also requires the
zero-based `platform` and integer `x`, `y`, `z`. `FINISH` requires those feet
coordinates; its platform field is unused. `FALL` and `RESTART` ignore position
fields. A missing required field is a 400.

Coordinates use the existing cube axes: negative coordinates are valid.
For a landing, x and z must be inside the platform footprint, and y must equal
the platform's top y plus one. Pickups require their exact feet cube; the future
client can report another `LAND` on the same platform when reaching that cube.
Every accepted state change increments revision. A repeated unchanged landing
does not increment it. Rejected gameplay reports return 200 with a result and
unchanged state, so a consumer must inspect `result` instead of counting HTTP
success as progress.

Illustrative fall command, using the actual run's current revision and a new UUID:

```json
{
  "commandId": "e38f2cf6-c29b-4254-9ed1-4a70e7c4c206",
  "expectedRevision": 4,
  "action": "FALL"
}
```

Retry the exact same normalized command and revision with the same command id
after an uncertain response. The last 32 receipts per run are retained. A changed
semantic payload with a retained id returns `COMMAND_CONFLICT`; stale revisions
return `REVISION_CONFLICT`. Original receipts can describe an older snapshot, so
read the current run before issuing a new command if later actions already ran.
Outside the bounded receipt window, an old state-changing command's stale
revision prevents reapplication. Opening a run is not idempotent; do not blindly
retry admission after an uncertain outcome.

The process admits at most 128 active runs and four per subject. It refuses new
admission when full, preserving active runs. Thirty idle minutes expire a run;
expiration is swept on access. A host restart discards practice state. Existing
world seed/style lookup is checked on each access. No baseplate cube map is held
in a run and no existing-world mutation is issued.

## Deferred acceptance

Source was inspected against the actual WorldHub, BricksOps, identity helper,
rate-limit configuration and controller conventions. Source inspection and Git
whitespace inspection are not compilation, test results or gameplay proof.

Later validation must exercise ordered progress, missed pickups, fall before and
after each bank, completion and restart, concurrent revisions, exact retries,
ownership, capacity/expiry, JSON binding, and default-off startup. A future host
owner must attach the pickup/HUD presentation and existing avatar landing/fall
events, show continuous movement on the current obby, and record actual runtime
use. Preserve the standard obby as the fallback if practice is unavailable.
