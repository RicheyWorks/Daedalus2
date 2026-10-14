# Native Synapse study desk

The study desk connects recall practice in the user's everyday realm to the running Synapse app. The native panel presents a desktop-approved card, reveals its answer only on request, then sends the user's explicit score to Synapse. The existing `Arc<StudyService>`, vault and SM-2/FSRS scheduler remain authoritative. A matching persisted app receipt is the only native saved-review signal; no review is simulated in the realm.

## Delivery and current work item

This increment implements the next missing native app connection after the photo terminal. It is **source only, UNVERIFIED**: tests, builds, UHT, service execution, installed module loading, placement and Play are deferred by the current instruction. Source inspection is not evidence that these behaviors have run. No personal vault, credentials, external service or fax transport was accessed.

The isolated stack starts at Daedalus PR154 commit `5e14c374de794a4bc78bf44ae0e80884f600664c`. That PR's native sources remain unchanged. Exact claim **31102**, continuation acceptance **31109** and coordinator acknowledgment **31115** cover six new Synapse sources, this guide and its install manifest, and updates to the two existing companion coverage documents. Existing Hero, Build.cs, launchers, game sources, art and maps are outside this change. The [four-app coverage map](../companion-apps-v1/capability-map.json) continues to expose incomplete Image Optimizer/fax/native verification work and desktop-only features.

Only `codex-play-guard` may perform eventual authorized native adoption. Source ownership or handoff receipt is not installation, visual approval or gameplay acceptance. The constructor cube is a placeholder; physical desk art and realm placement remain owner work. There are no newly authored assets, export recipes or measured performance results in this source increment.

## Existing app and user workflow

The app source is `RicheyWorks/synapse` draft PR3, commit `793de9fb005648efbb72ef018b71ee300f802522`. `synapse-desk/src/lib.rs` exposes the opt-in selected-track service; `synapse-core/src/service.rs` persists a review and its receipt together. `docs/STUDY_DESK.md` documents desktop operation. This delivery does not launch the app or change its installation.

After an authorized installation, the intended workflow is:

1. In the existing Synapse desktop, select a track and enable Study desk. The app grants 1–100 supported basic/cloze/code card IDs. New IDs and image cards remain excluded. The selection is an ID permission set, not an immutable snapshot of card content or later track membership.
2. Obtain a fresh private `http://127.0.0.1:<port>/realm/synapse/#token=<43-base64url-characters>` link without first consuming it in the browser. Each grant permits one session claim and expires after 15 minutes. Syntax and a draft source pin do not establish the running listener's identity or installed binary version.
3. Interact with `/Script/DaedalusLink.DaedalusSynapseTerminal` as the nearby local possessed Hero. Paste into the masked field and pair. The field is replaced after Pair/Close; capabilities are checked before the single session claim.
4. Read the first due card after pairing, or Refresh to request a due card and its app-masked cloze context. Recall the answer, then explicitly Reveal. Plain text and code are displayed without HTML, executable snippets, linked content or remote resources. Revealed cloze text currently includes its source markers as plain text; the desktop's formatted cloze rendering is not reimplemented here.
5. Choose 0 Blackout, 1 Wrong, 2 Wrong/familiar, 3 Hard, 4 Good or 5 Easy. The exact card ID, revision, score and new action UUID freeze together. A validated matching receipt with `persisted:true` confirms the save and provides the next-review information. Refresh for another card only after resolving that action.
6. If the response is lost, Retry same save reconciles or saves that exact action. Scores/navigation remain blocked while it is unresolved. A fresh approved pairing can recover the same receipt during this panel's lifetime. If the app requires reveal again, only explicit reveal of the original revision and explicit retry are allowed; another score/action is not substituted.
7. Disconnect requests app revocation; close/realm/reach/possession/focus/EndPlay also abandon the UI and attempt bounded cleanup. Revocation cannot undo a committed review. Closing loses the transient recovery tuple; an unconfirmed review may already be saved. Native memory is not a durable cross-process recovery store.

No endpoint exposes track enumeration, arbitrary vault browsing, settings, links, history, images/assets, imports, backups, file paths or schedule replacement. Those desktop features remain available in Synapse and are mapped separately.

## Actual service contract

Every request uses `Authorization: Bearer <pairing capability>`; claimed requests use `X-Desk-Session`. Every mutation includes the exact `Origin: http://127.0.0.1:<port>`, including native requests. Host stays literal loopback. Redirects, proxies, cookies, queries and returned URLs are not used. Capabilities, selected content and pending action state stay in private runtime memory, never class defaults, replication, saves, transactions, config, logs, analytics or NFT metadata.

| Route | Native binding |
| --- | --- |
| `GET /v1/capabilities` | Validate `productId:synapse`, `version:1`, `localOnly:true`, due/reveal/review/revoke actions |
| `POST /v1/session` | Single claim; HTTP 200 with `session`, `selected_count`, `expires_in_seconds` |
| `GET /v1/due` | Due count and nullable card: opaque ID, prompt, nullable context, revision, kind |
| `POST /v1/reveal` | Exact `{card_id,revision}`; tagged `basic/answer`, `cloze/text` or `code/language/code` |
| `POST /v1/review` | Frozen `{card_id,revision,score,action_id}`; direct persisted receipt, not a wrapper |
| `POST /v1/revoke` | Explicit `{}` and `revoked:true`; no review rollback |

Card IDs are opaque up to 64 UTF-8 bytes; imported IDs need not be UUIDs. Revisions are the app's 64 lower-case hex digest of the full item and must not be computed from projected fields. Empty text is valid. Prompt and supported answer content are bounded by the app at 32 KiB; the native JSON cap is 512 KiB to accommodate escaped prompt/context projections. Native transport also bounds headers at 8 KiB and request JSON at 4 KiB, uses a 3-second connect and 30-second request deadline, and gives shutdown revoke 3 seconds after the active request ends. One worker request is consumed through game-thread Tick; there is no automatic scoring or polling review.

A lost session-claim response has no recoverable session token. Repeating the claim could receive `already_paired`; require a new desktop grant, without claiming revocation was confirmed. `pairing_unavailable`/`session_required`, stale/reveal conflicts, failed saves, malformed receipts and interrupted transport do not become saved receipts. The same pending action survives a local disconnect/new pairing while this client exists. The app's persisted review/receipt and permission checks determine whether recovery succeeds. Unknown responses remain unknown until reconciled; no local cancellation or HTTP abort is presented as undo.

## Source review lessons and handoff

The reusable piece is the existing application service, not a replacement scheduler. The photo transport pattern provides bounded loopback worker mechanics; its plural sessions, session header, status code, UUID-only job IDs and small response allowance cannot be copied as a Synapse protocol. Source inspection caught these differences before authoring this adapter.

Independent client review also caught a receipt-identity mismatch: Unreal's default string equality is unsuitable for case-sensitive opaque Rust IDs. Receipt identity must compare equal lengths and exact code units, including embedded NULs, before acknowledging a save. This is a source correction, not execution evidence.

The actor preserves a matching local player's opening world/viewport and mapped Slate user, rejects other Hero overlays/paused worlds, and closes when the owner/realm/reach changes. UI-only mode prevents unhandled game actions. It does not take controller move/look ignore counters: Unreal's controller restart can reset them, making a later decrement consume another owner's state. PR154 correction 5e14c374 removes that edge and is inherited by this stack; source review does not establish runtime acceptance. Viewport restoration is independent of whether the opening controller survives.

The [install/binding manifest](install-binding-manifest.json) supplies six normalized source hashes, the exact base and app pin, class/interaction seam and deferred cases. Its containing delivery commit/PR head is the installation revision. No automatic checkout mutation, editor takeover, second editor, module reload, map save or service start is requested by this handoff.

Future owner evidence must separately establish compile/UHT/link/loading, actual installed app version, selected synthetic-card due/reveal/review receipt and persisted schedule readback, repeated/rejected/stale actions, uncertain-save recovery across pairing, revoke-versus-save ordering, lost claim, expiry and malformed responses, plaintext/privacy boundaries, local controller/focus lifecycle, physical art and Play. Dedicated tests remain deferred. No timings or runtime success are inferred from source size, source review, CI skipping or this document.
