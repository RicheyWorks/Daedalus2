# Local app machines, version 1

The image workbench and study desk are physical interfaces to the existing Image Optimizer and Synapse applications. Their encoders, schedulers and user data stay authoritative in those apps. The Unreal actor opens a local companion page; it does not encode images, grade cards, read files or claim a job finished merely because the browser opened.

## Native adapter

`ADaedalusLocalAppMachine` uses the existing `ADaedalusUsable` / Hero `Interact` seam. Set its `Application` preset to `ImageOptimizer` or `Synapse`. Claude owns the local player's runtime pairing UI, actor placement and Play acceptance. Blender physical art is a requested handoff, not an accepted delivery.

Call `PairLocalApp(link)` only with a private link obtained from the corresponding running app. The exact accepted forms are:

```text
http://127.0.0.1:<canonical-port>/realm/image-optimizer/#token=<43-base64url-characters>
http://127.0.0.1:<canonical-port>/realm/synapse/#token=<43-base64url-characters>
```

The port is 1024–65535. The token is 32 random bytes encoded as 43 unpadded ASCII base64url characters. The expected preset must match the exact entry path. Other hosts, alternate loopback spellings, credentials, queries, escapes, control characters, NULs and extra path/fragment components are refused. A typed path distinguishes companion interfaces; it does not cryptographically establish who owns a local listener. Pairing is a trusted local action.

Pairing is private, transient, nonreplicated, nontransactional and absent from saved maps, config, text export and actor defaults. Invalid pairing clears an old link. Runtime preset writes use `SetApplication`; actual changes immediately clear pairing, including switching away and back without Use. Editor property changes also clear pairing; undo cannot restore a capability. EndPlay clears pairing. A nearby local player in the same running game world can use the actor; editor worlds, remote pawns, local AI and dedicated servers cannot launch it. Failed launch attempts also consume the launch cooldown.

The native states are `Unpaired`, `Paired`, and `CompanionOpened`. None establishes an active app session or completed work. On Windows the shared guarded launcher calls the OS without parameters or URL/error logging; other native platforms fail closed. The original photo actor retains its original root URI grammar and behavior while sharing that launcher.

## Image workbench

The existing Swing app starts the companion only with `--realm-bridge`. Select PNG/JPEG files explicitly in the companion. Set quality, resize width and output format, then download each optimized image. The bridge accepts bytes and settings only, never filenames, input folders, arbitrary output paths or external image URLs. Originals remain untouched.

The desktop and companion use the same Thumbnailator encoder configuration. Original desktop folder planning, collision/alias checks, skip heuristic and duplicate controls remain intact. The companion has its own bounded job workflow and deliberately supports only PNG/JPEG. Widths 1–4096 and explicit PNG/JPEG output choices are companion additions to the existing desktop controls. JPEG loses transparency; re-encoding can increase size. Report measured source/output bytes rather than promising savings.

Authenticated `GET /v1/capabilities` identifies `productId: image-optimizer`, protocol `imageoptimizer.local.v1`, capability `image.optimize`, and actual limits. `POST /v1/sessions` creates a private expiring session; job routes require both process and session capabilities. `POST /v1/jobs` takes a stable `Idempotency-Key` and bounded `IOP1` envelope. Scoped status, output downloads and cancellation use that job ID. A conflicting body/settings with the same key fails. Canceled actions retain bounded tombstones until session expiry so a delayed retry cannot resurrect work. A new intentional action uses a new key.

The binary envelope uses big-endian integers: ASCII `IOP1`, uint32 image count, uint8 quality percent, uint8 resize flag, uint32 maximum width, uint8 output format (0 source, 1 PNG, 2 JPEG), then uint8 input type (1 PNG, 2 JPEG), uint32 length and image bytes for each image. No trailing data. Defaults: eight inputs, eight MiB/input, 24 MiB body, 4096 pixels/dimension, 12 million pixels/image, 24 million pixels/batch, 32 MiB total output/job. Decoded standard pixels keep source metadata out of exports. Cancellation/failure/revocation/expiry/shutdown removes partial files; stalled HTTP transfers have a deadline.

## Study desk

Synapse's native interface explicitly selects a track/card subset to share and can revoke it. The bridge stays off until the user enables it. It exposes a due card, reveals its answer only after an explicit action, and applies a score through the existing SM-2 or FSRS scheduler and atomic local persistence. The same transactional `StudyService` serves desktop commands and the desk, preserving vault format, settings, review history and statistics. This pilot excludes image cards to avoid exposing stored paths or fetching assets.

The desk has private process/session capabilities and a bounded selected-card set. It has no endpoint for listing the whole vault, filesystem paths, settings changes, import/export, deletion, backup restoration or sync. A review carries a stable action ID and expected revision. Repeated identical actions recover their persisted result; conflicting/stale actions fail rather than changing the schedule twice. Saves publish staged state only after persistence succeeds. A durable optional receipt in the review log supports restart recovery without a separate replacement vault.

Synapse uses `Authorization: Bearer <process capability>` plus `X-Desk-Session` after a single `POST /v1/session` claim. `GET /v1/capabilities` identifies `productId: synapse`, version 1. `GET /v1/due` returns a count and one approved card's ID, prompt, kind, revision and safely masked cloze context. `POST /v1/reveal` takes `{card_id,revision}`; `POST /v1/review` takes `{card_id,revision,score,action_id}` with a UUID and score 0–5. A new review requires reveal. `POST /v1/revoke` closes the listener and fences later saves. Pairing expires after 15 minutes. Only the native desktop selects a track; no HTTP endpoint enumerates tracks. Malformed cloze context is withheld before Reveal.

Native pairing opens the typed companion only; it does not send reviews, pass a local vault path or automatically opt the user into sharing. Test against generated temporary vaults, never the user's personal vault. The authoritative schema and limits live in [Synapse's study desk guide](https://github.com/RicheyWorks/synapse/blob/codex/realm-study-desk/docs/STUDY_DESK.md) and [Image Optimizer's bridge guide](https://github.com/RicheyWorks/image-optimizer/blob/codex/realm-image-optimizer/docs/REALM_BRIDGE.md). The [object catalog](objects.json) contains public interface metadata only; capabilities and personal data must never be inserted into it.

## Verification and handoff

Keep source core preservation, HTTP/service tests, original app regression checks, browser behavior tests, actual Unreal UHT/UBT/link, physical art, placement and Play evidence as separate stages. The browser automation runtime is currently unavailable in this environment; static/HTTP tests do not certify visual or live interaction behavior.

Codex owns the two app services and this isolated additive adapter scope. Claims and requested owner acceptance were sent in hub 28745–28748; Codex accepted the additive split in 28750. The previously accepted photo/fax service split is 28700. Claude owns native pairing/placement/live acceptance; Blender physical object art acceptance remains pending. The [art handoff](ART_HANDOFF.md) follows the shared queue's prop rules and proposes existing art first. Arcade, realm parity, inventory/dialogue, audio and the shared editor lease remain with their owners. Codex claimed the existing Java egg/catalog/realm fixture alignment in 28763; this adapter does not edit it.

No service is publicly deployed. No personal files are scanned, third-party data upload performed, provider credential added, real fax sent, paid service activated or NFT transaction made. Product ownership/license/access and future provider charges remain separately reviewed work.
