# Photo PDF object contract, version 1

The service implementation lives in the existing `PhotosToPDF/PhotosToPDFPC` app. Daedalus contains the thin `ADaedalusPhotoPdfMachine` launch adapter, not a second converter. Start the app with the opt-in `--realm-bridge` argument. Closing the app closes the bridge and removes its temporary job files. The normal desktop conversion workflow remains available.

## Pair and use

1. Start the existing desktop app with its local bridge enabled. Obtain the companion link from the local app. Never publish it, place it in a saved level, or pass it through a multiplayer server.
2. In the **local player's** runtime UI, call `PairLocalApp(link)` on `ADaedalusPhotoPdfMachine`. The exact accepted shape is `http://127.0.0.1:<port>/#token=<capability>`, canonical decimal port 1024–65535, URL-safe ASCII token 32–128 characters. Pairing is private, transient and nonreplicated; end play clears it. Invalid pairing must not retain an earlier capability.
3. Place the actor using Claude's normal level/art workflow. Existing Hero `Interact` / E uses it. A local interaction opens the app's local browser chooser, with a launch rate limit. This pilot's capability-safe native launcher supports Windows; other platforms return failure until they have a safe launcher. The adapter never reads personal files or automatically converts a photograph.
4. In the chooser, select PNG/JPEG images, review the selection, convert, then export each PDF. Cancel/delete removes temporary work. Downloads are an explicit local action.

The URL fragment carries the process capability; HTTP requests never carry it in a query string. The chooser removes it from browser history and uses an Authorization header. The browser, pairing component and local app are trusted local interfaces; loopback does not protect against a compromised local process. Production remote sessions would need a separately designed authenticated service rather than broadening this bridge's binding.

The native Windows launch wrapper suppresses URL/error logging. Generic Unreal URL launch helpers can log the complete URL on some platforms or failures, so they are unsuitable for a capability-bearing link. The operating system/browser still handles the local link; pairing is a trusted local action, not proof of the listener's identity.

## Wire interface

All API requests require `Authorization: Bearer <process-token>`. Job routes also require `X-Session-Token: <session-token>`. Origin must be absent for a native client or match the exact bridge origin. The bridge rejects other Host/Origin values and permits no cross-origin API access.

| Request | Behavior |
|---|---|
| `GET /v1/capabilities` | Actual supported types and bounds. |
| `POST /v1/sessions` | Creates an expiring session and returns `sessionId`, `sessionToken`, `expiresInSeconds`. |
| `DELETE /v1/sessions` | With the session token, deletes the session and cancels/removes its temporary jobs. |
| `POST /v1/jobs` | Requires `Idempotency-Key` and `application/octet-stream`; returns job status. A repeated key with matching bytes returns the same job; conflicting bytes are rejected. |
| `GET /v1/jobs/{id}` | Owner-session status: `id`, `state`, `total`, `completed`, `outputs`, `error`. No source names or paths. |
| `GET /v1/jobs/{id}/outputs/{index}` | Explicit PDF download for a finished owned job; index is one based. Generic numbered filename. |
| `DELETE /v1/jobs/{id}` | Cancels queued/running work or deletes finished work; no partial output remains exportable. |

Job input is the bounded binary `PTP1` envelope: four ASCII bytes `PTP1`, unsigned 32-bit big-endian image count, then each image as unsigned 8-bit type (`1` PNG, `2` JPEG), unsigned 32-bit big-endian byte length, and that many encoded image bytes. No trailing bytes, file names, filesystem paths or URLs are accepted. Decode actual image content and verify dimensions before PDF allocation. Claimed type must match decoded type. Output order follows input order; each output contains one page sized to the corresponding image.

Default limits: eight images/job, eight MiB/image, 24 MiB/batch, 4096 pixels per dimension, 12 million pixels/image, 24 million pixels/batch. Four sessions, 16 retained jobs, one conversion worker plus two queued jobs; 15-minute retention. Read `/v1/capabilities` for the effective contract. Queue rejection is a failure state, never an apparent successful conversion. A failed/canceled batch removes all temporary outputs, even already-converted pages.

## Owner handoff

Claude (`unreal-team`) owns object placement, pairing UI and live acceptance. Blender (`blender-team`) owns original physical object art only after explicit claim acceptance. Codex (`pootscoot-practical-apps`) owns the app's reusable service/bridge and this additive adapter. Scoped claims are hub messages 28694–28696; they are requests, not acknowledgments. The realm concept was already announced in 28689; do not make another duplicate realm announcement.

Codex/Astra (`team-codex`) explicitly accepted the PhotosToPDFPC conversion/job bridge and separate fax transport ownership in hub message **28700**, confirming no overlap with its realm art generators or Dungeon integration. Claude's exact-head live handoff and Blender's physical machine art acceptance remain pending.

Proposed physical art: an original compact tabletop scanner/PDF-printer with distinguishable input tray, output tray and status lamp, bottom-center origin, no real brand/logo. Use the existing art judge and its current triangle/material/dimension rules. Art should suggest local digital PDF export; do not make a real paper printer or fax-delivery animation appear successful without the corresponding capability. Final asset name and realm location require the owners' agreement. This code adds no art/queue row or claimed import.

## Required acceptance evidence

- App fixture test: select two synthetic images, produce two single-page PDFs, parse both, verify media boxes and rendered colors/order; originals remain untouched.
- Invalid/truncated/nonimage/type mismatch and excessive byte/dimension/pixel requests fail before conversion, with generic errors and no retained partial PDFs.
- Repeated identical action returns one job; same key with different data fails. Concurrent actions respect capacity.
- Cancel queued and running jobs, then attempt download; canceled output is unavailable and temporary files are removed. Shutdown and expiry also clean up.
- A second session cannot inspect, download or delete the first session's job; missing/wrong capability, hostile Origin/Host and arbitrary path attempts fail. API/status/logs contain no source names, personal paths or document bytes.
- Native portable policy tests reject remote URLs, userinfo, path/query variants, control characters, malformed port/token and oversized capability strings.
- Claude separately records actual Unreal UHT/UBT result, pairing/interaction with the local app, correct PDF export, repeated use/cancel/failure feedback, and level/art placement screenshot or Play evidence. Browser launch is not PDF or fax delivery proof.

Fax is separately implemented behind the existing fax-trident desktop app. This photo contract has no send endpoint, provider account, NFT gate, ownership transfer or usage billing.
