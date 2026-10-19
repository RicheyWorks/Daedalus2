# Activity result, version 1

One finished minigame, one subject, one credit.

Fishing, egg hatching, arcade cabinets, sports and mazes each end with a result. What Life Learns
needs a single shape for "this activity finished with this outcome for this subject", and a receipt
that credits that creature or plant exactly once when the same result is replayed, retried or
delivered twice.

This folder is the contract. The JDK-only core is `com.daedalus.world.activity`
(`ActivityResult`, `ActivityCredit`, `ActivityResultReceipt`, `ActivityCreditLedger`).
It does not import a game, a server, or a JSON library. The first wired game is Prismheart pond
fishing: `PrismPondFishing` reads a finished Windmere cast and the pond table
`daedalus.rpg-fish/v1` in `data/rpg/prism-fish.json`. A later game adds an adapter. It does not
invent a second envelope.

No XP curve is chosen here. The receipt records the lesson. A later progression step decides what
that lesson is worth.

## Fields

UTF-8 JSON object. Unknown fields are rejected. No partial credit.

| Field | Required | Rule |
|---|---|---|
| `version` | yes | Exactly `activity-result/v1`. Any other version is refused. |
| `activityId` | yes | 1–64 characters. `^[a-z0-9]([a-z0-9.-]{0,62}[a-z0-9])?$` |
| `attemptId` | yes | 1–64 characters. `^[A-Za-z0-9]([A-Za-z0-9._:-]{0,62}[A-Za-z0-9])?$` |
| `subjectId` | yes | Same token rule as `attemptId`. The creature or plant that learns. |
| `subjectKind` | yes | `CREATURE` or `PLANT`. |
| `outcome` | yes | `LEARNED`, `COMPLETED`, `MISSED`, or `FAILED`. |
| `learned` | yes | Same token rule as `attemptId`. The lesson, in every outcome including a miss. |
| `detail` | no | 1–8 entries when present. Keys `^[a-z]([a-z0-9-]{0,30}[a-z0-9])?$`. Values are printable ASCII, 1–96 characters. |

`attemptId` is the host's idempotency key for one finished attempt. A new cast, race, or hatch is a
new attempt and may teach the subject again. Replaying the same attempt is not a new lesson.

Do not put passwords, bearers, session tokens, or raw credentials in any field. The receipt id is
a hash of the envelope, so those fields are not a hiding place.

## Versioning

The version string and this folder move together. `activity-result/v2` would be a new folder and a
new `version` value. A v1 reader rejects every other version and does not guess. Adding a field is
a new version, because v1 objects reject unknown fields.

## Canonical bytes

`ActivityResult.serialize()` emits one compact JSON line, UTF-8, no trailing newline:

1. Keys in this order: `version`, `activityId`, `attemptId`, `subjectId`, `subjectKind`, `outcome`, `learned`, then `detail` only when it has at least one entry.
2. `detail` keys are sorted by Unicode code point.
3. Strings escape quotation mark, reverse solidus, and `U+0000`–`U+001F` (`\b` `\f` `\n` `\r` `\t`, otherwise `\u00XX`). Solidus is not escaped.

The receipt id is the lowercase hex SHA-256 of those exact bytes. The same envelope names the same
receipt on every JVM. Nothing in the id comes from a clock or a random source.

## Exactly once

The credit key is the triple `(activityId, attemptId, subjectId)`. `subjectKind`, `outcome`,
`learned` and `detail` are the body, not a second key.

`ActivityCredit.credit` issues `ActivityResultReceipt` or refuses:

- **Duplicate.** The triple is already credited and the canonical body matches. The lesson is not
  applied again. The exception carries the original receipt.
- **Conflict.** The triple is already credited and the body differs (a retry that changed the
  outcome, the lesson, the kind, or the detail). The first credit stands. The new body is not stored.
- **Another subject.** A different `subjectId` is its own credit, even when the attempt id is shared.
- **Another attempt or activity.** A different `attemptId` or `activityId` is its own credit.

`remember(receipt)` reloads a receipt the host already persisted. Remembering the same receipt
again is a reload, not a second credit. Remembering a different body for the same triple is a
conflict. After a restart the host must `remember` every credited attempt before it accepts a
replay, or a fresh ledger will credit the lesson again. This module is the guard, not a database.

`ActivityResultReceipt.issue(credit, result)` is the call a game makes. The ledger refuses the duplicate.

## Prismheart pond fishing

`PrismPondFishing` is the only game adapter. It does not roll the bite and it does not edit the
pond demo. The host passes the finished cast the demo already decided (`phase`, banner, species)
plus who is learning.

A cast credits only when `phase` is `done` and the banner is one of the three sentences in
`tools/rpg_demo/index.html`:

| Banner | Outcome | Lesson |
|---|---|---|
| `NEW! CAUGHT A <NAME> (<RARITY>).` or the same sentence without `NEW! ` | `LEARNED` | species slug (`Pond Perch` → `pond-perch`) |
| `IT GOT AWAY.` | `MISSED` | species slug of the fish the pond had already chosen |
| `TOO SOON. THE RIPPLE SCATTERS.` | `FAILED` | `ripple-scattered` |

`NEW!` is presentation. With or without it, the credit is the same lesson, so a replay that drops
the prefix is a duplicate rather than a second catch. The species and rarity on a caught banner
must match `data/rpg/prism-fish.json`. A too-soon cast has no species yet; naming one is refused.
An unknown species, a cast still `wait` or `bite`, and a catalog that is not `daedalus.rpg-fish/v1`
for realm `prism` are refused. No credit is issued for a refused cast.

The published example is a duneback (Prismheart mount, a creature) learning `reedling` from
Windmere cast `cast-windmere-7`.

## Fixtures

`prism-pond-caught.json` is valid. `prism-pond-caught.canonical.json` is the exact `serialize()`
line plus a trailing newline so the file is a text file. `missing-subject.json` is well-formed
JSON and an invalid envelope: `subjectId` is required, and a missing subject credits nobody.

`activity-result.schema.json` is the same field rules for a consumer that is not the Java core.
The schema cannot express the ledger. Exactly-once is this README plus `ActivityCredit`.
