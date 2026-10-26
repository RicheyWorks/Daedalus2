# Bot hub (the team link): real-time messages for every bot on this PC (ADR-053)

It started as the Blender team ↔ Unreal team channel and is now open to every bot. To join:
- pick a name (`lead`, `2hot2trot`, `art-master-flex`…);
- `POST /register {me, role, handles: [types you act on], about}`;
- heartbeat, then long-poll `/wait`. Add `&topics=art,plan` to get only those topics' broadcasts; messages sent to
  you by name always come through.

`GET /bots` is the directory: who is registered, their role, the message types they handle, and whether they're
alive. `GET /` is a live dashboard in the browser.

A bot that sends more than 20 messages a second (bursts up to 200 are fine) gets `429`, so one noisy bot can't slow
the rest. This is the load-shedding idea from LoadBalancerPro. Catching up from any id reads only the new part of the
log.

## Bots that can't open a socket: the file bridge

A sandboxed bot (PootScoot, the Codex bot, is one) uses two files under `bot-team\link\`. Its name is NAME.
- **To send,** append one JSON object per line to `outbox\NAME.jsonl`:
  - `{"to": "lead", "type": "note", "body": {"text": "hi"}}`: a message.
  - `{"ack": 42}`: a receipt for message 42.
  - `{"heartbeat": "working on black jack"}`: I'm alive, and what I'm doing.
  - `{"register": {"role": "...", "handles": [...]}}`: who I am and what I take on.
- **To read,** look at `inbox\NAME.jsonl`: everything for NAME, one message per line, each delivered once.
- The hub picks up outbox lines within half a second and keeps its read position across restarts. A half-written
  line waits for its newline.

## The art pipeline on the hub

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

## Turns and answers (2026-10-13, Richmond: "I need you two talking in real time")

Editor turns and the merge queue are **locks on the broker**, not prose. A claim is refused with who holds it; a
holder that goes quiet loses the claim after its TTL (30 min default); claims are log lines, so they survive a
restart. Unanswered requests to you are your **inbox**.

```
python -m asset_pipeline.teamlink claim unreal --me unreal-team --note "build 56ce68bbc"     exit 0 claimed, 3 refused (and a note is posted)
python -m asset_pipeline.teamlink claim merge-queue --me team-codex --note "57-72"
python -m asset_pipeline.teamlink release unreal --me unreal-team                            --force takes it from a quiet holder
python -m asset_pipeline.teamlink locks                                                       who has what, for how long
python -m asset_pipeline.teamlink inbox --me unreal-team                                      requests/pings to me that I have not acked, oldest first, with age
python -m asset_pipeline.teamlink ack 28937 --me unreal-team                                  I handled it: it leaves my inbox, the sender gets a receipt
python -m asset_pipeline.teamlink watch --me team-codex --minutes 60                          a terminal: one line per message as it arrives
```

6. **Claim before you touch a shared editor** (`unreal`, `blender`) or the merge queue (`merge-queue`); release
   when done. `CLAIM`/`RELEASE` in a status text no longer counts.
7. **Ask with `type: request`** addressed to the bot (not `*`) when you need an answer; the other side sees it
   in `inbox` until it acks. Answer with `reply_to` set and ack it. Check your inbox at the start and end of every
   slice and whenever you are waiting on a build.
8. HTTP: `POST /lock {me, name, note?, ttl?}` (409 + the holder when refused), `POST /unlock {me, name, force?}`,
   `GET /locks`, `GET /inbox?me=`.

For a durable agent inbox, safe retries and explicit task acceptance, use
[`asset_pipeline.live_handoff`](TEAM-HANDOFF-LOOP.md). Poll at tool/job boundaries and during build waits.
Its `accepted`, `blocked` and `completed` replies are distinct from the broker's receipt ACK. It works on
the existing broker endpoints; a terminal watcher alone does not make an idle agent respond.

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
python -m asset_pipeline.teamlink send --me blender-team --to unreal-team --type asset.ready --asset Tool_Axe
python -m asset_pipeline.teamlink send --me blender-team --to unreal-team --type note --text the axe head is 0.3 m
python -m asset_pipeline.teamlink wait --me blender-team --after 0
python -m asset_pipeline.teamlink presence
python -m asset_pipeline.teamlink ping --me blender-team --to unreal-team
```

From Python, use `asset_pipeline.teamlink.Link("blender-team")`. It has `.send`, `.wait`, `.ack`, `.heartbeat`,
`.pending`, `.inbox`, `.lock`, `.unlock`, `.locks` and `.presence`, and it never raises when the broker is down;
`.up` turns False instead.

## Keeping it running

`connectors\claude-asset-pipeline\teamlink.ps1` takes `-Start`, `-Status`, `-Ping` and `-Stop`. The Unreal team's
watcher (`art-queue.ps1`) joins the link automatically. With the link down, the watcher falls back to its 10 s
board pass, so nothing stops.

## The Blender team's dialect (BUS-SCHEMA v1), on the same log

Their client (blender-harness `bus.py`) finds the broker through `bot-team\art\BUS.json`, which the broker writes
when it starts. It speaks an envelope:
`{v: 1, id: uuid, from: "blender", to: "unreal", type, asset, at, reply_to, body}`.

| Endpoint | What it does |
|---|---|
| `GET /v1/health` | `{ok, v: 1, last}` |
| `POST /v1/messages` | Takes an envelope. A repeated `id` is ok and is not stored twice, so outbox replay is safe. |
| `GET /v1/messages?to=blender&since=<their uuid or our seq>&wait=<s>` | Returns envelopes oldest first. Add `wait` to long-poll. |
| `GET /v1/status` | Returns presence and the last id. |

How their names map to ours:
- `blender`/`unreal` ↔ `blender-team`/`unreal-team`.
- `ready` → `asset.ready`.
- `status` → `blender.status`, which also feeds presence.
- Our `asset.shipped` and `queue.waiting` reach them as `shipped` and `waiting`.
- `reply_to` carries their own uuid back.
- Their `ack` with `reply_to` is a receipt.

## Build art in your own cloud, not on Richmond's PC (ADR-058)

Blender runs fine headless in a cloud sandbox (`pip install bpy`), which frees the PC's RAM for Unreal. Ship from the
cloud like this:
1. In your cloud Blender, export the asset's meshes to `<Asset>.glb`, with modifiers applied and +Y up. Write
   `<Asset>.sent.json` beside it: `{"objects": [{"name", "triangles", "materials": [...], "dims": [x, y, z]}]}`, which
   is what Blender says it sent (the same fields `asset_pipeline.sides.BLENDER_EXPORT` reports).
2. Put both files in `bot-team\art\<Kind>\` on the PC, with no `.blend`, and set the row READY in QUEUE.md.
3. The watcher imports the glb with no Blender on the PC. The judge still checks your report against the file and the
   file against Unreal, so a wrong report is REJECTED, not shipped.

**Replacing art that's already shipped:** a `<Asset>.glb` plus `.sent.json` that is at least as new as the asset's
`.blend` wins, so a cloud rebuild never needs the old `.blend` deleted. `tools/claude_island/orr_hq.py` is the worked
example: it rebuilds all 509 Orrery Reach items with bevels, more segments, smooth shading and metal or gloss
materials, and checks each glb against its report with the judge before keeping it.
`orr_hq_sheet.py` renders a before/after sheet.
