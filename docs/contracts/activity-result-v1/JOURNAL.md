# activity-result-v1 receipt journal and replay (contest G49)

Durable storage for settled receipts, so What Life Learns survives a restart.

## Wire and journal form

- `ReceiptCodec.parse(json)` reads the canonical single-line form that `ActivityResultReceipt.toJson()` writes. It is strict: it re-serialises what it parsed and refuses input that differs at all. That covers spaces, reordered keys or measures, extra fields, string escapes, a wrong `schema` and trailing bytes. So a parsed receipt always has the digest it was written with.
- `ReceiptJournal` is append-only UTF-8 text with one receipt per line: `<sha256 hex> <canonical json>`.
  - `line(receipt)` writes a line and `read(line, lineNo)` checks one.
  - `readAll(lines)` / `read(path)` read the whole journal (a missing file counts as empty); `append(path, receipt)` adds a line.
  - A bad digest or non-canonical JSON throws `TamperException`, which names the 1-based line. Blank lines are skipped.
  - Nothing is ever rewritten or removed.

## Router

- `ActivityRouter.journal()` returns every receipt that `settle` or `credit` accepted, oldest first, one line per source key.
- `ActivityRouter.credit(receipt)` credits a receipt that was already issued, under the activity's current policy. The receipt must match the adapter's definition revision and mode. If the same source key arrives with a different digest, it throws `ProgressionLedger.ConflictException`.
- `ActivityRouter.replay(lines)` rebuilds progression after a restart. It checks every line before it credits any of them, so one tampered line means nothing is credited. Each receipt is credited exactly once, so replaying the same journal twice pays nothing the second time. It returns the number of new receipts.

## Example

```java
ActivityRouter live = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
live.settle("sports.catch-rally", session, rally);
for (String line : live.journal()) { /* persist line */ }

ActivityRouter restarted = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
restarted.replay(Files.readAllLines(journalFile)); // same totals, credited once
```

Tests: `daedalus-core/src/test/java/com/daedalus/world/activity/ReceiptJournalTest.java`.
