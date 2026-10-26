# Portal quest progression core

The portable C++ core adds ordered step progression without changing existing
RealmCore or quest data. Royal audience, rescue and unicorn request adapters can
supply authoritative event IDs, step types and stable target IDs. The current
test demonstrates those paths; no NPC or inventory binding is installed yet.

Only matching current steps advance. Successful event IDs cannot be replayed,
counts saturate without unsigned overflow, and reward claiming yields one signal
per in-memory instance. The host must validate events and atomically persist
progress with inventory awards. Reconstructing a fresh instance loses replay
history: this is not a durable reward service or authorization boundary.

Limits are 32 steps and 512 accepted events per quest instance. On event capacity
exhaustion progress stops with CapacityReached; it never evicts history. A host
must constrain quest definitions/event granularity or provide durable processing
before production integration. No save/restore or restart-safe reward claims are
provided in this first core.

MSVC C++17 with /W4 /WX passed 531 checks, including replay, out-of-order events,
wrong targets, overflow-sized amounts, capacity exhaustion and single claims.
Unreal module compilation and live gameplay acceptance remain pending.
