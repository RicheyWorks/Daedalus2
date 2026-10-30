# Dock travel contract

User clarification, 2026-10-13: boats and submarines waiting at docks are the entrances to the Ocean realm. Ordinary land disembarkation returns to the departure realm; underwater docks let submarines reach other connected realms.

Claude's remote main `56ce68bbcc241097db57409e3737fbb106b9de45` implements the realm-session rules in `DaedalusRealmSessionCore.h`. Inspected directly from fetched Git content; the shared local checkout has not been changed.

| Journey | Native session request |
| --- | --- |
| Docked boat enters Ocean | `SwitchRealm("OCEAN", "dock", "boat:<dock-id>")` |
| Docked submarine enters Ocean | `SwitchRealm("OCEAN", "dock", "sub:<dock-id>")` |
| Ordinary shore landing | departure realm, `shore` |
| Submarine reaches another realm's underwater dock | destination realm, `dock`, `sub:<dock-id>` |

These are routing rules, not proof of a completed world load. Ocean dock eligibility, authority, actual vessel identity, possession and safe landing must remain validated. Coordinate transaction order with Claude so a failed board or failed destination load cannot strand a hidden passenger or publish the wrong realm. Do not independently replace Claude's Hero/session implementation.

Current private harbor inspection: original skiff, submarine and dock imported into Unreal; 64 Ocean chunks rendered. Packaged Java server plus native inspection scenario completed in 35.281 seconds. Its proof explicitly leaves rendered gameplay and realm transfer unverified. A combined interactive boarding, sailing/diving, landing and destination-streaming test remains required.

## Canonical realm IDs in the vessel route policy

The portable Ocean route policy now recognizes `OCEAN` and `PORTAL`, matching the session and Java
directory. It also retains the legacy `Ocean Realm` and `Portal Realm` spellings. Host registries
must use one spelling consistently: dock, registered realm and vessel current-realm fields still
match exactly. A registry containing both aliases of the same realm is rejected atomically.
The route returns the destination spelling stored by the host, so configure canonical IDs when
feeding destinations into RealmSession. This is not fuzzy name matching or a global alias registry.

MSVC C++17 /W4 /WX passes 98 checks, including the original legacy routes and refusals plus exact
canonical Portal boat departure/return and Ocean-to-Gallery submarine routes checked against the
session planner. The expanded test fails with exit 1 against the previous header and passes with
the fix. No Hero, session, possession or live editor code was changed. Registered directed routes,
underwater/boat restrictions and dock identifiers remain enforced.

Remaining gap: the vessel policy's ordinary non-underwater destination remains Portal-only,
whereas the session allows returning to its recorded departure realm. Returning to a different
departure realm needs an authority-bound departure record in the vessel/transaction adapter,
not permission for an arbitrary shore destination. Neither this fix nor its tests prove that
transaction, actual possession, rollback, streaming or rendered cross-realm travel.

Integration lesson: use exact IDs from the consuming session in route tests, in addition to
human-readable test names. Legacy fixtures alone could not catch canonical destinations being refused.
