# Opt-in Ocean host API

The server can now host one configured Ocean sector using OceanChunkWindow and
OceanChunkStore. Enable daedalus.ocean.enabled=true and provide directory and seed.
Resident capacity defaults to 128; chunk bounds default to x/z -2..1, y -3..0
(the exported 64-chunk sector). Configuration refuses invalid/overflowing bounds
or more than 4096 chunks. Choose separate directories/bounds for separate hosts;
distributed district routing and lease coordination are not implemented here.

GET /api/v1/ocean/v1 returns the realm id, decimal seed string, generator version,
chunk size, configured bounds, resident capacity and dock/boat/submarine anchors.
GET /api/v1/ocean/v1/chunk?x=0&y=-1&z=0 returns existing ChunkBlocksResponse:
4096 base64 block ordinals with the existing palette and empty-chunk convention.
No alternate terrain wire format or palette ordinal was introduced.

Both routes require a nonempty authenticated principal, including when the
outer development security chain permits requests. Use the production profile's
existing JWT resource-server setup for authenticated network access; this patch
does not add a development token decoder. The feature is disabled by default.
Ocean reads have a separate oceanChunks per-key limiter (32 requests/second by
default), so maze generation and sea reads do not spend one another's quota.
Outside-sector requests return 404 before terrain generation; corrupt storage
returns 503 without exposing the store path. There are no HTTP edit endpoints.
Trusted Java host code can call the service's set method only after enforcing
its own player/land ownership policy; that policy is not supplied by this API.

The service owns/releases its store on application shutdown. This is a bounded,
synchronous local host API: operator scheduling, global I/O capacity, per-player
range tickets, public hosting/TLS/backups and capacity tests remain necessary.
The sector-volume cap bounds possible chunk addresses, not total production cost.

Validation: 18 Ocean core tests plus 14 server/auth/error-contract tests passed.
The full application booted under prod+test on random loopback ports, verified
missing/invalid JWT refusal, valid manifest/chunk payloads, outside-sector 404,
independent subject quotas and 429, then shut down and restarted with a host edit
intact. A corrupt cold record produced 503 with no filesystem path in the body.
Unit checks cover default-disabled configuration and bounded-sector validation;
the explicit production auth table and published README table remain in parity.
Reactor time was 52.029 seconds; the real HTTP/restart test body was 6.652 seconds.
These times are scoped test runs, not load or gameplay benchmarks.

See ocean-host-api-proof.json. New Windows/Ubuntu CI repeats these checks. Shared
SecurityConfig, WorldHub, WorldService and the Unreal loader are unchanged. The
sector is not automatically registered in /worlds, and no player is moved into
it by these routes. Native authenticated client binding, server realm registration
and actual dock-to-realm transition/visible Play acceptance remain open.
