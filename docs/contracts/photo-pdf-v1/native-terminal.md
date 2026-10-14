# Native photo/PDF terminal

This source extension connects the existing PhotosToPDFPC service to an in-world panel. `ADaedalusPhotoPdfMachine` remains the existing browser-launch object. The additive `ADaedalusPhotoPdfTerminal` provides a local selected-image workflow through the existing service; it contains no PDF converter. The application's `RealmPhotoBridge` still calls the shared PDFBox conversion primitive and produces one image-sized, single-page PDF per photo.

## Current delivery stage

New implementation is **source only and unverified**. Dedicated tests, builds, UHT, service requests and native operation are deferred by the user. Earlier pilot tests/builds belong to earlier source commits and do not establish this new terminal's behavior. No terminal is installed, bound, placed or accepted in Play by this delivery. The sole native operator is `codex-play-guard`.

Coordinator acknowledgment is hub **31050**, accepting the exact claim in **31039**. Operator acknowledgment **31054** confirms source ownership without installation or runtime acceptance. This claim adds eight uniquely named native source files and four contract/map files. Existing launchers, Hero, Build.cs, JavaArcade/Blackjack PR152, Minesweeper PR139, CSRBT PR153, Flowers and other owners' files remain outside this change. The full four-app [coverage map](../companion-apps-v1/capability-map.json) tracks remaining features instead of declaring the portfolio complete.

## Existing app prerequisites

- PhotosToPDF companion draft: `RicheyWorks/PhotosToPDF` PR3, source `7927f75f1e347fdb0c75a0af27b46f6f89b34ebc`.
- Existing desktop launch: from `PhotosToPDFPC`, `mvn javafx:run -Djavafx.args="--realm-bridge"`, or the already packaged app with `--realm-bridge`. This document executes neither command and installs no software.
- The user obtains the running app's private pairing link from its desktop pairing control. The native terminal supports literal `http://127.0.0.1:<port>/#token=<capability>` using the existing `DaedalusPhotoPdfCore` grammar. No automatic process discovery or app activation is added.
- The bridge must actually be present in the user's local app installation. A GitHub draft or matching link syntax does not prove the installed binary's version or listener identity. Handshake checks `protocol: photospdf.local.v1` and `outputMode: one_pdf_per_photo`; this protocol has no `productId` field.

## Native user flow

1. Interact with the terminal as a nearby local player in a running game world without another Hero overlay open. The panel uses UI-only input without pausing the world. Windows is the first supported file-dialog platform; dedicated servers, remote pawns, AI and editor worlds cannot operate it.
2. Paste the private app link into the masked field and pair. The input is cleared. Only a valid capabilities response followed by session creation establishes a connected session.
3. Choose up to eight PNG/JPEG files through an explicit local file dialog. The client reads only those selections. It sends typed image bytes in a `PTP1` envelope, without filenames, paths or URLs.
4. Convert through the existing app. The panel reports the actual job state/progress. It does not count URL parsing, pairing, transport dispatch or a busy animation as successful conversion.
5. Once the whole batch is reported `SUCCEEDED`, choose each numbered PDF output and an explicit local destination. Native download and export share a 64 MiB per-PDF cap; an oversized output fails explicitly rather than being saved as a partial document. Export refuses existing targets, stages a new sibling file, and commits without replacement. Original images and existing documents are not overwritten. PDF header/end-marker checks are local envelope checks, not structural PDF validation.
6. Cancel/delete removes the owned app job. Disconnect revokes the session. Closing the panel, leaving reach/realm, possession changes or actor EndPlay abandons the UI and requests bounded best-effort session cleanup. An unconfirmed cleanup is not a deletion receipt; the app's retention/expiry and shutdown policies remain authoritative.

The selected-byte bridge intentionally restricts formats and size. Original desktop folder/output planning, collision-safe names, broader desktop formats and table workflow remain in PhotosToPDFPC. Directory scanning, multi-page merging, OCR, physical printing, fax sending and native PDF rendering are not introduced. See the coverage map for unbound desktop features.

The Windows helper retains and validates directory handles through selected-file reads and PDF commit/cleanup. It rejects reparse/mount/network paths, path aliases that do not match normalized handle paths, unsupported local volume resolution and directory chains over 128 ancestors. Its temporary export remains owned through [non-replacing by-handle rename](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_rename_info) or failure disposition; it never reopens a temporary filename for cleanup. These are reviewed source rules; Windows filesystem and dialog behavior still require the deferred operator exercise.

## Existing wire contract, reused

All requests are direct loopback HTTP with redirects and proxies disabled. Native bounds are 32 KiB JSON, 8 KiB total response headers, 64 MiB PDF, a 3-second connect deadline and a 30-second request deadline. Progress polls at most once per second and stops on errors; shutdown cleanup has a 3-second revoke deadline after aborting the active request. These bounds do not guarantee every backend-valid photo will export. Process authorization is `Authorization: Bearer <capability>`; session requests additionally use `X-Session-Token`. Capabilities remain transient process memory. Nothing stores them in maps, transactions, replicated state, logs, config, analytics or NFT metadata.

| Route | Native binding |
| --- | --- |
| `GET /v1/capabilities` | Protocol/output mode and effective bounds handshake |
| `POST /v1/sessions` | Existing plural session creation, retaining returned session capability privately |
| `POST /v1/jobs` | Exact `PTP1` binary bytes with a stable `Idempotency-Key` |
| `GET /v1/jobs/{uuid}` | Explicit refresh and bounded progress polling |
| `GET /v1/jobs/{uuid}/outputs/{index}` | Authenticated owned PDF bytes; local destination is chosen separately |
| `DELETE /v1/jobs/{uuid}` | Explicit cancellation/deletion, followed by confirmed local action reset |
| `DELETE /v1/sessions` | Explicit revoke and lifecycle cleanup |

Job/output URLs are constructed locally from validated UUIDs and bounded one-based indices. Returned paths are not followed. Response errors use generic local messages. The existing server remains responsible for image decoding, CRC/format/dimension validation, conversion, ownership, queue limits and partial-output cleanup.

An uncertain submission freezes its exact action ID and bytes. Retry recovers that same action; it cannot silently change the selection or create a replacement. Cancellation with an unknown job first reconciles the same action. Within a live session, the client resets its key/selection after confirmed job deletion, which releases the server key. Confirmed session revocation or authorization loss clears local session state; explicit shutdown abandons that state after its bounded cleanup attempt without claiming remote deletion. If a session-creation receipt is lost, no returned session capability is available to revoke and app expiry remains authoritative. This differs from Image Optimizer's retained cancellation tombstones and Synapse's durable review receipts; the protocols are not interchangeable.

## Native binding handoff

The machine-readable [install/binding manifest](install-binding-manifest.json) records exact files and deferred stages. `codex-play-guard` alone decides an installation/application window under the existing editor ownership. No second editor, editor restart, map mutation or service activation is requested from a source worker.

After an authorized source installation, bind `/Script/DaedalusLink.DaedalusPhotoPdfTerminal` through the existing `ADaedalusUsable` / Hero Interact seam. Place an additive actor with operator-chosen art and realm placement; the constructor's engine cube is a placeholder, not approved physical art. There is no pairing URL class default or level property to fill. Pair only through the local player's open panel.

Future acceptance must separately establish compilation/loading, matching installed app service, actual selected-image conversion and export, uncertain-action recovery, cancellation/disconnect cleanup, file overwrite refusal, controller/focus/realm lifecycle, physical art and Play evidence. Those actions are deferred, not performed by this document. The helper and client are source implementations until their exact delivered revision is exercised by the authorized owner.
