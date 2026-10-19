# activity-result-v1: shared activity-result envelope and ActivityResultReceipt

Contest gap **G12** (minigame contest 2026-10-19, owner 2hot2trot). Implements life-progression **step 3**
("Connect one real activity") from the life-progression and minigames spec (*What Life Learns*): one versioned
envelope around existing games, one immutable receipt, one award per life and track, exactly once.

Java: `daedalus-core/src/main/java/com/daedalus/world/activity/` (tests in the matching test package).

## Pieces

| Type | Role |
| --- | --- |
| `ActivityDefinition` | Versioned contract around one existing game: adapter id, revision, realm, mode, allowed life profiles and roles, bounded measures (`0..max`), max participants. |
| `ActivityParticipant` | Accepted participant: `lifeInstanceId` (`LIFE`) or `colonyInstanceId` (`COLONY`), profile and role keys. Species keys are never changed. |
| `ActivityResultAdapter<R>` | Interface: map a game's own result `R` plus host session facts into a receipt. One adapter per game; the game keeps its rules. |
| `ActivityResultReceipt` | Immutable receipt. Canonical JSON (`toJson`) and SHA-256 `digest`; `sourceKey` = activity, session and result. |
| `AwardPolicy` | Owner-approved weights and cap that turn measures into points for one track. `AwardPolicy.inactive` (default) records contributions and grants 0 points. |
| `ProgressionLedger` | Reference progression authority: credits each participant once per `(sourceKey, instanceId, track)`. |
| `ChalkTrailRunAdapter` | The one real game wired in: the Labyrinth `ChalkTrail`. |

## Rules (what the tests check)

- A client never supplies XP. Receipts carry bounded game measures; the policy computes points.
- `DEVICE_LOCAL` results (browser timers, cabinet scores, exported saves), `ABANDONED` and `DISCONNECTED` outcomes pay 0.
- Retrying the same receipt returns the earlier awards. Reusing a result id with a different payload throws `ConflictException` and changes nothing.
- A new policy or adapter revision does not make the same event payable again (the award key ignores revisions).
- Unknown measures, out-of-bound values, disallowed profiles or roles, duplicate participants and over-sized parties are rejected when the receipt is issued.

## Wire form

`example-receipt.json` is the exact canonical output of `ActivityResultReceipt.toJson()` for the test receipt
(the test fails if they drift). `chalk-trail-definition.json` documents the Chalk Trail definition.

## Daedalus tie-in: the Chalk Trail companion

A companion walks the Labyrinth with the player and helps chalk the route. When the run ends, the host builds a
receipt from the trail it already owns (marks kept, chalk spent, exit reached), and the companion earns
**scouting** mastery: "listen to the maze before trusting a map". Peaceful scouting is a full growth path with no
kill count, and a hive can join in an observation role as a colony, credited once. Chalk eaten by a Chalk Eater
still counts as spent, so the companion learns from effort rather than from what survived.

## Adding another game

1. Write an `ActivityResultAdapter<YourResult>` with its own `ActivityDefinition` (new `activityId`).
2. Keep the game's rules where they are; the adapter only maps facts to measures.
3. Credit through `ProgressionLedger` (or a persistent authority that keeps the same award key) with an
   owner-approved `AwardPolicy`; until then use `AwardPolicy.inactive`.

Award curves, caps and per-track numbers remain an **owner decision**; the values in the tests are examples only.
