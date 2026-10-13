# Native Ocean host client

UDaedalusOceanHostClient is a local read component for the opt-in Ocean API.
ConfigureSession takes a trusted root server origin and a login bearer token.
It accepts HTTPS DNS/IPv4 origins, or HTTP on exactly 127.0.0.1 for local tests.
Userinfo, paths, fragments, invalid ports and token header-injection characters
refuse. Credentials are private ordinary strings, not reflected/config/saved or
replicated properties, and this module never logs them. This is not memory
zeroization, login/session issuance or a completed TLS/redirect security audit.

RequestChunk permits one request in flight, with a 10-second timeout and a
64-KiB response stream cap. Completion runs on the game thread. ClearSession,
component destruction and EndPlay cancel work and advance a generation guard,
so stale replies cannot update a new session. An invalid ConfigureSession call
leaves the previous session intact. These APIs belong on the game thread.

The decoder validates expected signed chunk coordinates, finite exact numeric
revision up to 2^53-1, required boolean/data fields, unique bounded palette names
with AIR at ordinal zero, canonical base64, exactly 4096 bytes and each ordinal's
palette bound. An empty chunk becomes 4096 AIR bytes; malformed replies clear
output rather than publish partial state. OnChunk supplies a snapshot to the
caller; this component does not create scene meshes or move the player.

Failures report sanitized status/reason, never server bodies or credentials.
The underlying engine HTTP backend controls redirect/TLS transport behavior;
checking the returned URL is not proof that no credential was forwarded during
a redirect. Production redirect/pinning policy remains a separate gate.

Verification passed: complete 131-file plugin, 46 actions in 193.26 seconds;
final EndPlay update rebuilt five actions in 12.40 seconds. All three native
Ocean tests passed with zero test errors/warnings. Packaged Java production
server to native client transport passed in 21.188 seconds including startups:
water payload, 404 bounds, 401 invalid JWT, cancelled reply rejection and reconnect.
All 131 production inputs matched the committed manifest; two external fixture
files were declared. See ocean-client-build-proof.json,
ocean-client-runtime-proof.json and ocean-client-http-proof.json.
The probe uses temporary test JWTs in
child environment variables, binds only loopback, changes no shared editor/world,
and will not be counted as rendered gameplay or cross-realm travel.
