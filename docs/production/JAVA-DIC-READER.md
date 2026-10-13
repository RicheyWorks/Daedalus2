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
