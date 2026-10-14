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

### Effective URL validation

UE 5.8 retains the original request URL in GetURL() after a redirect. The old
comparison therefore accepted redirected chunk data. The client now compares
GetEffectiveURL() to the exact requested URL with case-sensitive matching before
publishing a payload. Resource path case is significant.

The original native baseline accepted both a same-origin path redirect and a
cross-port redirect (ocean-redirect-baseline-proof.json). With the fix, four fresh
UE processes accepted the direct response and refused path, port and path-case
redirected payloads in 38.407 seconds including startup. The production snapshot
dab439d6 built all 148 tracked files in 220.56 seconds and passed five native Ocean
tests. Adding the two declared external probe files rebuilt 52 actions in 261.13
seconds. Production hashes were checked before the HTTP probes; fixture hashes
and the resulting module hash are recorded separately.

See ocean-effective-url-build-proof.json, ocean-effective-url-runtime-proof.json,
and ocean-effective-url-redirect-proof.json. These snapshots predate later main
metadata/quest fixes; they do not claim a full build of those later changes.
The source candidate passes the main plugin preflight after merging those fixes.

The transport still contacted redirect destinations. The fresh fake credential
was forwarded on same-origin redirects and withheld on the observed cross-port
redirect. Token text was absent from probe logs. Payload refusal does not prevent
credential forwarding and does not prove TLS, pinning, public hosting or a
production redirect policy. Those release gates remain open.
