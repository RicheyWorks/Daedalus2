# Provider-aware realm discovery

Authenticated `GET /api/v1/realms` lists the realm providers hosted by this server.
World Zero and other mounted WorldHub worlds retain their existing order and
routes. The already-configured Ocean provider is appended only when its opt-in
bean exists. Discovery never mounts a world, copies terrain into WorldService,
generates a chunk, or changes an ownership record.

The schema is version 1. `chunkSize` is 16 and `coordinates` is
`xyz-y-up-metres`, the Java block convention. Every realm entry has:

| Field | Meaning |
| --- | --- |
| `id` | Storage world identity, unique across providers |
| `title` | Existing world title, or Ocean |
| `realm` | Optional canonical native session ID, such as `GALLERY-CITY` |
| `catalog` | Optional DIC/DCS file stem, such as `gallery-city` |
| `protocol` | `WORLD_V1` or `OCEAN_V1` |
| `manifestPath` | Same-origin manifest route |
| `chunkPathTemplate` | Same-origin block DTO route with `{x}`, `{y}`, `{z}` chunk coordinates |
| `blockEditsSupported` | Whether the provider exposes block edits; this grants no caller permission |

For Ocean the manifest is `/api/v1/ocean/v1`, the chunk template is
`/api/v1/ocean/v1/chunk?x={x}&y={y}&z={z}`, and edits are unsupported.
For a mounted world `gallery`, the manifest is `/api/v1/world/gallery` and the
chunk template is `/api/v1/world/gallery/chunk/blocks?x={x}&y={y}&z={z}`.
Both providers use the existing ChunkBlocksResponse payload and palette.

Known storage IDs map only when their WorldStyle matches: `world-zero` maps to
`WORLD-ZERO`/`world-zero`; `gallery` or `gallery-city` to
`GALLERY-CITY`/`gallery-city`; `parcels`, `bricks` and `labyrinth` to their uppercase
session IDs and lowercase file stems. Ocean maps to `OCEAN`/`ocean`, matching
DaedalusRealmSessionCore. Unknown custom worlds and aliases with a different
style leave both optional fields unset. A catalog stem identifies content; it
does not assert that the catalog is installed. In particular the current server
loads five shipped catalogs, and the Ocean content catalog remains separate work.
`PORTAL` has no chunk provider entry.

The native client matches the session Current() to `realm`, not to storage `id`.
Two mounted aliases claiming the same canonical session (for example both
`gallery` and `gallery-city`) make discovery refuse rather than choosing a first
match. No custom world is silently reassigned to a game's canonical session.

Clients substitute integer chunk coordinates before resolving a template against
the configured server origin. Fetch that entry's manifest and obey its bounds;
do not send Ocean requests to WorldHub's WorldService routes. Discovery and Ocean
reads require authentication even outside the production filter chain. Directory
requests share the existing per-subject `oceanChunks` quota, so cache directory
metadata instead of requesting it for every chunk.

If a mounted WorldHub world already uses `ocean` while the Ocean provider is
enabled, or canonical session IDs collide, discovery returns 503 with a generic reason. It never shadows an entry
or moves/deletes existing data. Resolve the configuration conflict explicitly.
The response contains no storage paths, seed, token, external server URL or
private configuration. Disabled Ocean does not appear.

This is discovery on one server. It does not register Ocean as a WorldService,
grant player travel or editing permission, choose district servers, load Unreal
sectors, or prove public hosting. Those integrations remain separate work.

Validation includes immutable provider ordering, disabled/enabled Ocean, no
generated chunks during discovery, duplicate identity refusal, identity checks
outside the production chain, source/README authentication parity, and actual
production JWT HTTP discovery followed by a chunk read using the advertised
route. The existing Ocean persistence/restart and quota assertions still run.
