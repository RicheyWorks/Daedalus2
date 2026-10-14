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
