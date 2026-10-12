# Team link: the Blender team ↔ Unreal team real-time channel (ADR-053)

One small broker on Richmond's PC at `127.0.0.1:9890`. It uses only the Python standard library and stores its log
in `bot-team\link\log.jsonl`. QUEUE.md stays the official record. The link is how each team hears about a change
the moment it happens, and how each team knows the other one is alive.

## Names

The two teams go by `blender-team` and `unreal-team`. `*` means everyone. Other names are allowed; Richmond's tools
use `ping-<user>`.

## Rules

1. **Heartbeat** at least every 10 s: `POST /heartbeat {"me": "blender-team", "status": "building Tool_Axe"}`. You
   count as alive when your last beat (or a send, or a wait) is under 30 s old.
2. **Listen with a long poll**: `GET /wait?me=blender-team&after=<last id you saw>&timeout=25`. It returns the
   instant something for you arrives. Keep `after` as the `last` it hands back.
3. **Acknowledge** every message you handled: `POST /ack {"me": "blender-team", "id": 42}`. The sender gets a
   receipt (`type: "ack"`).
4. **After a restart**, catch up first with `GET /pending?me=blender-team` (messages to you that you never
   acknowledged), then wait from `/health`'s `last`.
5. **Send**: `POST /send {"from": "blender-team", "to": "unreal-team", "type": "asset.ready", "body": {"asset":
   "Tool_Axe"}}`. You get back `{"id": n}`.

## Message types

| type | from → to | body | what happens |
|---|---|---|---|
| `asset.ready` | Blender → Unreal | `{asset}` | The Unreal team's watcher sets the row READY, adding it to QUEUE.md if it isn't there, and ships it **now** instead of on the next 10 s pass |
| `asset.shipping` / `asset.shipped` / `asset.rejected` / `asset.blocked` / `asset.waiting` / `asset.error` / `asset.added` | Unreal → `*` | `{asset, result? / why? / detail?}` | Live results. `rejected` means the asset needs a fix; `blocked` means Unreal's fault, retried in 60 s |
| `queue.waiting` / `queue.resumed` | Unreal → `*` | `{why}` / `{waited_s}` | What the queue is stuck on (Blender closed, Unreal in Play…) |
| `queue.status` → `queue.state` | either | `{}` → `{waiting_on, counts}` | The board in one round trip |
| `ping` → `pong` | either | `{}` | Proves the other side is alive end to end |
| `note` | either | `{text}` | Words for the other team (and Richmond) |
| `ack` | broker | `{id, type}` | The receiver has your message |

Any other type passes through untouched, so new types need no broker change.

## From a shell

Run these in `Daedalus2\connectors\claude-asset-pipeline`:

```
python -m asset_pipeline.teamlink send --me blender-team --to unreal-team --type asset.ready --body "{\"asset\":\"Tool_Axe\"}"
python -m asset_pipeline.teamlink wait --me blender-team --after 0
python -m asset_pipeline.teamlink presence
python -m asset_pipeline.teamlink ping --me blender-team --to unreal-team
```

From Python, use `asset_pipeline.teamlink.Link("blender-team")`. It has `.send`, `.wait`, `.ack`, `.heartbeat`,
`.pending` and `.presence`, and it never raises when the broker is down; `.up` turns False instead.

## Keeping it running

`connectors\claude-asset-pipeline\teamlink.ps1` takes `-Start`, `-Status`, `-Ping` and `-Stop`. The Unreal team's
watcher (`art-queue.ps1`) joins the link automatically. With the link down, the watcher falls back to its 10 s
board pass, so nothing stops.
