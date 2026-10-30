# Lantern Reach exploration slice

Source-only **UNVALIDATED**, owned by `codex-buckwild-n64`, exact hub claim 30729.
This is an original, provisional N64-era-inspired exploration design. Its names,
layouts, movement tuning, collectible thresholds and modular kit are proposed
choices within the user's approved direction. No canonical N64 identity was
found in the inspected registry. `lantern-reach` identifies this design; it is
not an allocated session realm, a WorldStyle, a provider ID or a land deed.

The existing asteroid/shattered-planet/ark canon stays intact. A small surviving
lantern archive connects three compact fragments. The warm Atrium shows a vista
inside each arch, so players can recognize a destination before entering it.
Wide steps, ramps, catwalks and landmarks support exploration; hidden reed
curtains, service hatches and star shutters reward curiosity. Names and content
are original; no art, characters, levels or logos from another game are copied.

## Defined content and progression

`LanternReachDefinition.create()` provides immutable data for one hub and three
compact themed worlds, six directed portals, nine unique lantern seeds,
fourteen objectives, six reusable module types and twenty-four placements.
These are source definitions, not generated/imported geometry or playable proof.
XYZ points use metres with **Y up**; a native host must apply its existing
coordinate and scale conversion. Module sockets describe kit intent and do not
claim physical snapping, collision or traversal validation.

| World | Exploration and optional discovery | Atrium entry requirement |
| --- | --- | --- |
| Lantern Atrium | Broad ascent overlooking all three portal previews | Initial hub |
| Reedbell Ravine | Bank, bridge, high bell; quiet curtain and hidden seed | Open |
| Coppercloud Works | Court, copper catwalk, relay; service hatch and hidden seed | Any two unique seeds plus Ravine summit objective |
| Moonseed Observatory | Ramps, launch terrace, dial; unlit star and hidden seed | Any five unique seeds plus Works relay objective |

Every destination has a free return portal to the Atrium. Seeds are retained,
never spent by travel, and each seed can be recorded once. All three destination worlds have
separate visit, landmark, visible-seed-pair and secret-path objectives. Objectives
can be pursued in any order inside a world; the generic definition also supports
acyclic objective prerequisites. Unlocks are derived from confirmed unique seed
and objective state. With two visible Ravine seeds and two visible Works seeds,
the Observatory's five-seed threshold asks the player to find at least one
optional hidden seed; either earlier world's secret works.

Walking, hopping, ledge climbing and a short Observatory glide are movement
intent in data. No existing controller behavior is replaced. A preview renderer,
native movement/collision host and marker/collectible witness are still required.

## Core and host boundary

Four new files in `daedalus-core/.../world/exploration/`:

- `ExplorationDefinition.java`: bounded, immutable world/portal/objective/module
  records; reference checks, acyclic prerequisites, hub reachability and free
  return-route checks. A disconnected or invalid definition is rejected.
- `LanternReachDefinition.java`: the original content above; no automatic
  registration, bean discovery or asset import.
- `ExplorationProgress.java`: pure initial snapshot and candidate transition.
  Events are `CROSS_PORTAL`, `REACH_MARKER` and `COLLECT`, each with an ID,
  expected logical revision and design target. Visit/landmark/collection
  objectives are derived. Locked destinations and wrong-world events are refused.
- `ExplorationHostAdapter.java`: disabled by default. An explicit owning host
  binding supplies its approved canonical realm ID, authenticated subject,
  witnessed event and existing durable compare-and-swap publication.

The snapshot binds schema 1, exact design/version, canonical realm and subject,
logical revision, current world, visited worlds, reached markers, collected IDs,
derived completed objectives and accepted event history. All collections are
immutable. Restore deterministically replays the entire retained history and
compares the exact snapshot. A definition version change needs an explicit
owner-reviewed migration; it does not silently reuse old progress.

Replay retains at most **512 accepted events without eviction**. A matching ID
and full event payload returns `REPLAY`; reusing that ID with different revision,
action or target returns `CONFLICT`. A new event with an old revision is `STALE`.
Repeated marker/seed targets under a new ID change nothing and consume no replay
entry. Every candidate reserves enough remaining event slots for its shortest
free return route to the Atrium; near capacity, exploration stops while return
travel remains possible. At capacity in the hub, further accepted transitions stop; a future durable authority
may extend/rotate history only with its own reviewed replay contract. This first
slice cannot provide indefinite travel after 512 accepted transitions.

The core's logical candidate is not a persisted result or an inventory reward.
The adapter exposes `COMMITTED` only when its existing host confirms exact
durable candidate publication. `CONFLICT` requires a fresh host read; an uncertain
write returns `UNCONFIRMED` and must be reconciled before retry. No in-memory
candidate is installed as authoritative progress on a refusal or uncertain save.
The host must serialize writes per subject and/or use its established atomic CAS.

An owning host integration follows this sequence:

1. Allocate/approve the real realm identity using the existing session and
   provider-directory ownership process. Do not add this design ID to global
   registries merely because a content definition exists.
2. Resolve subject identity from the authenticated principal, authorize that
   subject for the selected realm and load its actual host snapshot.
3. Validate real source-world proximity, movement or pickup against authoritative
   position/collision/ownership before accepting the candidate. Definition
   metadata and client requests alone are not evidence.
4. Publish snapshot and complete replay history through the existing durable host
   transaction with exact expected state/revision. Return `SAVED` only after the
   chosen authority confirms the candidate. An exception/timeout is uncertain.
5. Present confirmed world/portal/objective state through the existing native
   renderer/controller/UI. Any canonical inventory reward is a separate existing
   authority transaction; this slice makes no NFT, currency, mint or item grant.

The adapter is plain Java, not an active REST endpoint. `bind(...)` creates an
opted-in instance; constructing `new ExplorationHostAdapter(definition)` leaves
it disabled. No default canonical realm ID, persistence codec, new store, service,
timer or controller is installed.

## Existing interfaces preserved and current evidence

The inspected native registry is `DaedalusRealmSessionCore.h`; server provider
bindings are `RealmDirectoryService`. Both remain unchanged. The existing 8-bit
realm stays **PORTAL / The Portal Realm**, generated title **SHARDLANDS**;
`GET /api/v1/retro/{seed}` generates instances, and Sol Reach is a district of
that realm. This slice does not turn an example in `REALMS.md` into an existing
N64 allocation, or increase the count of current 8-bit realm families.

Baseline at worktree creation was freshly resolved `origin/main`
`a4991909361caec166932d6faa00a32f4356df74` (the earlier realm audit used
`e8d9aac382731bd02965e150aa821ace3b7420cb`). The canonical board claim and hub
30729 preceded these new files. Existing Session/WorldStyle/directory/catalog,
Hero/controller, progression authority, inventory, storage, security, importer,
harness, Blender and editor source are untouched.

Manual source/reference/contract and whitespace inspection are the only checks
for this delivery. Tests, compilation, CI, services, builds and native/editor
use remain deferred by user direction. Canonical identity allocation, durable
host binding, actual art/terrain, portal previews, collision, movement and
playable acceptance remain open with their existing owners.
