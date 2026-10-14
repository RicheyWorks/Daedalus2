# Native Image Optimizer workbench

The workbench connects explicitly selected local images and optimization controls in the everyday realm to the existing Image Optimizer app. It submits bytes to `RealmImageBridge`; the app's shared `ImageOptimizationService.optimizePixels` / Thumbnailator encoder remains authoritative. The native module contains no replacement encoder or folder scanner. This is the next concrete app connection after photo/PDF and selected-track Synapse.

## Delivery stage and scope

This delivery is **source only, UNVERIFIED**. Tests, builds, UHT, CI invocation, service activation, installed module loading, editor operation and Play are deferred. No personal images were read or submitted. Source review, a successful push or an installation handoff is not a verified image result.

The isolated stack starts at corrected Synapse source `c3f842214e921c9597dcd5400dd52028e440f0c2` (PR156), whose direct parent is the separately published photo input-ownership fix `5e14c374de794a4bc78bf44ae0e80884f600664c` (PR154). That correction was published and the clean single-commit Synapse stack verified before this increment began. Existing photo/Synapse native sources and other owners' Hero, Build.cs, launcher, game, art and map files remain unchanged here.

Exact Image scope claim **31169** and root ownership acceptance **31174** cover eight new Image Optimizer client/terminal/panel/file-helper sources, this guide and its install manifest, and the two existing companion coverage documents. The retained practical-app owner lane was accepted in **31050/31115**. The inspected hub/open-PR records contained no competing Image claim. Coordinator note **31188** confirms no overlap with recorded owner paths and preserves the already authorized direct-user source scope without an extra acknowledgment gate; it adds no publication/native authority or runtime acceptance. Only `codex-play-guard` may eventually adopt the native class. Physical workbench art/placement and live acceptance remain pending; the cube is a placeholder.

## Existing app and intended workflow

The pinned companion is `RicheyWorks/image-optimizer` draft PR4, source `486a121c2da6d320045f2447739f2b65c9bc88b3`. Its existing opt-in startup is `java -jar target/image-optimizer-1.0.0.jar --realm-bridge`; this document does not run that command or verify an installed binary. The desktop's Realm workbench control supplies the private literal `http://127.0.0.1:<port>/realm/image-optimizer/#token=<43-base64url-characters>` link. A link's syntax is not listener identity or installed-version proof.

After an authorized installation:

1. Interact with `/Script/DaedalusLink.DaedalusImageOptimizerTerminal` as a nearby local possessed Hero. Paste the app link into the masked field and pair. Check product/protocol/capabilities before creating a session; clear the visible link afterward.
2. Explicitly choose 1–8 PNG/JPEG images through the Windows picker. Only those selected regular local files are read. No filenames, paths, output destinations or directory walks enter the wire protocol.
3. Choose integer quality 70–95, optional resize with maximum width 1–4096, and Keep format / PNG / JPEG. Native initial controls are quality85, resize off, width1280 and Keep format; they do not change desktop/browser defaults. The width remains valid even when resize is off. The app reduces large images without enlarging small ones. JPEG loses transparency; outputs may be larger, and PNG quality semantics differ from JPEG. No size-saving percentage is promised.
4. Optimize through the existing app. Settings and the complete typed-byte envelope freeze with one action key. Actual server job status/progress drives the panel; dispatch, pairing and busy indicators do not mean success.
5. After whole-job `SUCCEEDED`, inspect each output's actual source/output bytes and encoded dimensions. Explicitly export each PNG/JPEG to a new matching filename. Existing source images and destination files are not overwritten. Native MIME, length and header-dimension checks are not a full pixel decode or proof of metadata removal.
6. Retry an uncertain submission using the exact same key, settings and bytes. Repeated unchanged completed actions refresh the existing job. Do not change controls or select a replacement batch until the action is resolved.
7. Cancel/delete confirms cancellation or receives an authenticated owned-job `NOT_FOUND` before retiring the local action and allowing deliberate new work with a fresh key. A confirmed canceled key/job remains a server tombstone until session expiry; it is not a released photo-style key. Missing access is not a physical-file deletion receipt. Unknown submissions reconcile the frozen action before cancellation, or revoke the session. A failed recovery blocks replacement work.
8. Disconnect revokes the session. Closing, owner/realm/reach/focus changes or EndPlay abandon the panel, invalidate export generations and request bounded best-effort revoke. Unknown cleanup remains unknown; the app's expiry/retention policies remain authoritative. Already exported user files remain. Four sessions and sixteen retained actions include canceled/failed/completed work; reconnect with a new session when the process reaches that action limit.

The original desktop file/folder planning, duplicate detection, existing-output skip heuristics and broader workflow remain available in the app. This selected-byte interface does not expose them. No merge/archive, arbitrary server path, third-party upload, external activation, credential creation, physical printing or fax transmission is added. Remaining desktop-only and fax gaps stay visible in the [coverage map](../companion-apps-v1/capability-map.json).

## Actual wire contract and bounds

Every `/v1/*` request uses the process Bearer capability; session/job requests additionally use `X-Session-Token`. The literal loopback Host is exact. Native may omit Origin; if supplied it must equal the origin. Redirects, proxies, cookies, queries and returned URLs are not used. Capabilities, image bytes, settings and action keys remain transient private memory, never maps, class defaults, replicated state, saves, config, logs, analytics or NFT metadata.

| Route | Native binding |
| --- | --- |
| `GET /v1/capabilities` | `productId:image-optimizer`, `protocol:imageoptimizer.local.v1`, `image.optimize`, `one_image_per_input`, actual limits |
| `POST /v1/sessions` | Empty body, HTTP201 with sessionId/sessionToken/expiresInSeconds |
| `POST /v1/jobs` | Stable Idempotency-Key and exact `IOP1` binary body, HTTP202 new / HTTP200 same action |
| `GET /v1/jobs/{uuid}` | Actual QUEUED/RUNNING/SUCCEEDED/FAILED/CANCELED snapshot |
| `GET /v1/jobs/{uuid}/outputs/{index}` | Owned, locally constructed route; image/png or image/jpeg bytes |
| `DELETE /v1/jobs/{uuid}` | Confirmed canceled snapshot; retained key/job tombstone |
| `DELETE /v1/sessions` | Revoke session and remove its jobs/keys |

The big-endian envelope has a **15-byte** fixed header: `IOP1`, uint32 count, uint8 quality, uint8 resize, uint32 width, uint8 output format. Each image adds uint8 source type, uint32 length and exact bytes. This is seven bytes longer than the photo header. Source types are 1 PNG / 2 JPEG; output format0 keeps each source type, 1 forces PNG, 2 forces JPEG. The entire envelope, including settings, participates in idempotency.

Source bounds are 8 files, 8 MiB each, 24 MiB complete framed request; 4096 per dimension, 12M pixels/image and 24M pixels/batch. The encoded output cap is **32 MiB for the entire job**, not per file. Successful metadata has index/name/width/height/bytes/sourceBytes/downloadPath and no format field. The client infers the expected type from frozen settings/source types, checks exact sourceBytes and generated name/path, and sums the output budget. Output routes use validated canonical UUIDs and bounded one-based indices, not arbitrary returned paths.

Native transport limits are 32 KiB JSON, 8 KiB total response headers, a 3-second connect and 30-second request deadline, with a 3-second lifecycle revoke after the active worker ends. Progress polling is at most once per second and stops on errors. One serial worker owns HTTP data; game-thread Tick consumes guarded completions. Failed/malformed/oversized/interrupted responses never become successful export receipts. A lost session-creation response has no session capability to revoke; cleanup remains unconfirmed and app expiry is authoritative.

## Local files, source review and handoff

The Windows helper follows the reviewed Photo file-ownership pattern in uniquely named additive source. It retains root-to-parent directory handles, rejects reparse/mount/network aliases, checks resolved local volume paths, and holds the owned temporary handle through failure disposition or non-replacing rename. It never deletes a temporary by reopening its pathname. Paths and ancestor counts are bounded; unsupported aliases/volume APIs fail closed. Explicit chooser cancellation is neutral, not a failed conversion or a fake export. No service chooses the user's local output path.

The actor inherits the corrected UI-only viewport ownership design without controller ignore-input counters. It binds the opening local player's world/viewport and mapped Slate user, rejects other Hero overlays/paused worlds, and restores only owned state. Image selection and export re-check the weak actor, panel generation and local owner around native dialogs. Cancel, disconnect and close invalidate delayed export callbacks.

The [install/binding manifest](install-binding-manifest.json) records exact normalized source hashes, source/app dependency pins, class/seam and deferred acceptance. The containing delivered commit/PR head is the installation revision. No second editor, restart, live service request, map write or automatic installation is requested by this source handoff.

Future owner evidence must separately establish compilation/UHT/link/loading; actual installed companion identity; synthetic PNG/JPEG quality/resize/format jobs; decoded dimensions/colors/alpha and metadata sentinel removal; original hashes; whole-job byte/pixel limits; strict frame and invalid-file handling; cross-session ownership; frozen settings/bytes retry; retained canceled tombstones/new keys; cancellation during upload/conversion/download; failed/expired/revoked cleanup; overwrite refusal and write/commit failure; modal/actor/controller/focus/realm lifecycle; physical art and real Play. Dedicated tests remain deferred. No timings or observed speed/size improvement are invented here.
