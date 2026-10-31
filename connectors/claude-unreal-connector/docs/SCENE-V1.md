# Read-only scene observations, schema 1

`scene_snapshot` and `scene_verify` are READ commands on the existing bridge. They reuse the actor-info
serializer with full numeric precision; `get_actor_info` retains its existing fields and rounding.
The legacy lookup now accepts a full object path and refuses ambiguous labels/names.

## Snapshot

Request params: optional `folder` (null or string), `offset` (integer >= 0, default 0), and `limit`
(integer 1..128, default 32). Folder matches itself and descendants, not unrelated prefix names.

Result fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | Integer 1. |
| `context` | `{session_id, world_path, world_kind, world_epoch}`; all nonempty strings, kind editor/pie. |
| `available` | Boolean; false means observation failed, not an empty scene. |
| `scope` | Loaded-only, non-atomic coverage and paging fields below. |
| `actors` | Actor values sorted by exact full path before paging. |
| `errors` | Up to 128 explicit path/serialization errors, with nullable path and code/message. |

Scope contains `loaded_only:true`, `atomic:false`, `folder`, `offset`, `limit`, `total_loaded`,
`total_matching`, `matched_known`, `returned`, `complete`, `next_offset`, `error_count`, and
`errors_truncated`. `total_matching:null` means a catalogue error prevented a reliable count.
`total_loaded:null` means enumeration failed. Serialization errors preserve the known matching count.
`total_loaded` counts the eligible actors returned by the active world's enumeration API, not every
actor physically loaded in that world. The installed UE 5.8 editor actor subsystem excludes pending-kill,
noneditable, non-outliner, template, and transient actors, plus the builder brush and WorldSettings.
Play totals cover the game-world API's returned set; they do not imply the same editor eligibility filters.
`complete` is true only for an error-free response containing the entire filtered API-returned set, starting
at offset zero. A final page with a nonzero offset is still incomplete. `next_offset:null` means no
more known paths; it does not repair unknown coverage. Pages are fresh observations and can change
between calls. They do not form an atomic snapshot, and unloaded World Partition actors are excluded.

Actor values include legacy label/name/class/folder/transform/bounds/components plus `path`,
`class_path`, nullable `parent_path`, and boolean `selected`. Components include full `path`, name/class,
and, for static-mesh components, nullable mesh and ordered nullable material-slot paths. Parent paths
may refer outside the filtered page. Scene serialization caps components and material slots at 128;
an overflow or non-finite/opaque value makes the actor unavailable rather than silently truncating it.
If an actor's serialized path differs from its catalogued path, it is omitted with an
`ACTOR_UNAVAILABLE` identity-change diagnostic. The response remains incomplete; records are not silently
reordered to conceal a changed identity. The native actor enumeration is not preemptible or bounded by
this page-size limit.

## Verification

Request params:

```json
{
  "schema_version": 1,
  "context": {"session_id": "from snapshot", "world_path": "from snapshot",
              "world_kind": "editor", "world_epoch": "from snapshot"},
  "actors": [{"path": "exact path from snapshot", "expected": {
    "location": [0, 0, 0], "parent_path": null, "selected": false,
    "components": [{"path": "exact component path", "mesh": null, "materials": [null]}]
  }}],
  "tolerance": {"location": 0.01, "rotation": 0.1, "scale": 0}
}
```

`actors` contains 1..128 unique exact paths and nonempty expected predicates. Supported predicates are
location/rotation/scale (three finite numbers), nullable parent_path, boolean selected, and a list of
component checks. Each component check requires an exact path and mesh and/or materials. Empty
`components:[]` explicitly expects no components; a nonempty list checks only named components.
Material arrays compare ordered slots exactly, including nulls and length. Empty `materials:[]` expects
no slots. Tolerances default to zero, must be finite/nonnegative, and apply per coordinate. Location is
cm, scale is unitless, and rotation is pitch/yaw/roll degrees with angle wrapping. This compares Euler
coordinates, not arbitrary equivalent quaternion representations. Unsupported or malformed predicates
raise an `expected_schema` ValueError before native reads; they cannot produce a successful empty check.

The result contains `schema_version`, current `context`, boolean `passed`, and `checks`. Each check has
`path`, `status` (`match`, `mismatch`, or `unavailable`), nullable `observed`, and `mismatches`.
Mismatch entries contain `predicate`, `expected`, `observed`, and optional `code`. Missing components
and unsupported component fields remain explicit even when expected and observed happen to be null.
Checks for unloaded/deleted/renamed actors do not fall back to labels. Unknown catalogue coverage uses
`ACTOR_UNOBSERVABLE`; duplicate full paths use `AMBIGUOUS_ACTOR_PATH`.
A path change between catalogue lookup and serialization returns `unavailable`, `observed:null`, and an
`ACTOR_UNAVAILABLE` identity-change diagnostic. Matching values under a different observed path cannot
verify the requested identity.

Verification may include `observation_errors`, `error_count`, and `errors_truncated` for catalogue errors.
`passed` applies only to the explicitly requested predicates, not whole-scene completeness. A known
valid actor can be checked despite an unrelated unobservable actor. Top-level `STALE_CONTEXT`,
`WORLD_UNAVAILABLE`, or `OBSERVATION_UNAVAILABLE` returns `passed:false` and no checks; this is not
an ordinary value mismatch or a proven empty scene. Transport `status:ok` does not imply `passed:true`.

## Identity and acceptance limits

Session IDs change on module reload. Epochs rotate on observed world kind/path/native-repr changes.
The implementation retains value strings only; no world/actor references or listener/event hooks persist.
UE 5.8's inspected PyWrapperObject repr includes the native object address, but it is an identity hint,
not a generation counter. Reuse of a native address, an unobserved switch away/back, or a same-path
reload may evade this hint. Paths/epochs are not rename-proof permanent IDs. Verification is read-only
and does not authorize later writes based on a stale context. Native lifetime/event fencing is a later
independent slice, as are event deltas and generic reflection schemas.

[Epic's UE 5.8 actor subsystem](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/EditorActorSubsystem?application_version=5.8)
documents eligible loaded editor-actor enumeration. Play observations use the game world, never an editor fallback
when Play's world is unavailable; selection is empty in Play. Current local acceptance uses offline
fixtures; hosted checks for this exact implementation are pending. Shared-editor validation remains
owner-controlled.

Fixtures: `tests/fixtures/scene_v1_offline.json` contains actual adapter envelopes made with fake_unreal,
explicitly marked offline, covering matching, mismatching, unavailable, stale, empty and paged results.
No live editor capture or scene preservation is implied.
