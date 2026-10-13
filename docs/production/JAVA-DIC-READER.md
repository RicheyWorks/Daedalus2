# Shared per-realm inventory catalog reader

InventoryCatalog adds an immutable Java DIC 1 reader based on Claude's
DaedalusInventoryCore.h at main 1c987e09. It preserves ordered tabs, equipment
slots, item actions, details, theme and realm identity. Duplicate definitions,
unknown tabs/slots and EQUIP without a slot are rejected. Parsing does not change
player counts or transfer items between realms.

Three targeted Java tests passed with repository Checkstyle. They cover ordered
immutable parsing, invalid references and native carriage-return/repeated-space
conventions. Full-file differential parity and server loading/transaction binding
remain pending. Tests do not establish an authoritative inventory service.

Use existing Content/Inventory/*.dic files as the runtime source, rather than a
second Java item catalog. Resource packaging and realm key mapping must be
connected before runtime adoption. Extensible action names match the native
format; the host must still validate permissions and apply effects atomically.

Runtime integration now embeds the canonical five DIC files in daedalus-core's
jar using Maven resources (no content filtering or separate Java catalog).
InventoryCatalogService validates all five realm identities on startup and serves
read-only definitions at GET /api/v1/inventory/{realm}/catalog. Unknown realms
return 404. Existing production default-authenticated security applies; this adds
no permit-all rule. No player bags, ownership or item effects are returned.

Tests load all canonical files, verify distinct realm content, reject path-like
realm lookup, and exercise HTTP JSON/status serialization using standalone MVC.
Full deployed-server auth/packaging smoke tests and C++ differential parsing
remain pending. Ocean and Portal catalogs are not fabricated from art rosters;
they still need authoritative item definitions and native catalog support.

Differential parity now passes all five canonical files and four corrupted
refusals. The actual native reader (unchanged from main 1c987e09) and Java reader
dump ordered UTF-8 field encodings; the comparison includes realm/theme, tabs,
slots and every item's ID/tab/slot/name/detail/action sequence. Local native
adapter compiled with MSVC /W4 /WX. CI runs the same comparison using GCC.
This closes full-file parser parity, but not deployed auth or item transactions.

Production-profile local HTTP verification now passes: the endpoint is explicitly
registered as authenticated in ProdAuthPostureTest and the README API table.
Real booted-server tests refuse unauthenticated requests, serve GALLERY-CITY
definitions with a test JWT, expose no player quantity/count fields and return
404 for an authenticated unknown realm. Four posture tests pass alongside the
catalog/realm integration tests. Public deployment, packaged-server smoke and
authoritative item transactions remain pending.
