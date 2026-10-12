# ADR-053: The team link, a real-time channel between the Blender and Unreal teams

Status: accepted, 2026-10-12

## Why

Richmond asked for "a robust harness that communicates between you 2 real time." The art queue (ADR-051) is a
Markdown board read every 10 s. It is a good record, but the teams talk through it slowly:
- a READY row waited up to 10 s;
- results showed up only when someone reread the board;
- neither side could tell whether the other side was alive.

## Decision

- **One local broker**, `asset_pipeline.teamlink`, on 127.0.0.1:9890. It uses only the Python standard library.
- **The log is append-only** (`bot-team\link\log.jsonl`). Each line is fsynced, ids only go up, and a torn last
  line is skipped on restart. The log stays on this PC, not GitHub.
- **Long-poll `/wait` wakes the instant a message lands.** No polling interval.
- **Every message can be acked.** The sender gets an `ack` receipt, and `/pending` replays unacked messages after a
  restart.
- **Heartbeats feed `/presence`.** A team is alive while its last beat is under 30 s old.
- **The Unreal team's watcher joins the link.**
  - It waits on the link instead of sleeping.
  - `asset.ready` sets the row READY, or adds the row if it's missing, and ships it at once.
  - Every queue event goes out live to `*` as `asset.*` or `queue.*`.
  - It answers `ping`, and answers `queue.status` with the board's counts.
  - With the broker down, it falls back to the 10 s board pass.
- **QUEUE.md stays the record.** The link carries the news.

The message types are in `docs/TEAMLINK.md`. Unknown types pass through, so the Blender team can add its own
without a broker change.

## Proven

- `harness/teamlink_test.py`, 34/34. It covers:
  - ordering and addressing;
  - a waiter woken in under 1 s, not on a poll;
  - receipts, idempotent acks and pending;
  - presence ageing;
  - a restart over a torn log;
  - HTTP 400s that leave the broker up;
  - a dead broker that never raises;
  - a live ping/pong;
  - the watcher: asset.ready to READY to shipped broadcast, rows added and numbered, pong, queue.state, everything
    acked.
- 4/4 mutants caught: no notify, ack ignored, own messages echoed, everyone always alive.
- `run_all` 5/5.

## Held

- The Blender team's own client. They are building it, and this spec is what it targets.
- Claude itself is not a resident listener (a session can't idle on a socket). The always-on `unreal-team` agent
  is the watcher. Claude reads `/log` and answers `note`s when active.
