# Practical apps as realm objects

The physical object is another interface to Richey's existing desktop app. The useful work stays in that app's implemented service. The first pilot is PhotosToPDFPC from [PhotosToPDF](https://github.com/RicheyWorks/PhotosToPDF); fax-trident is the explicit follow-on because the school fax machine was unreliable. A reusable interface is useful only when it preserves the application's real behavior and failure states.

This change adds a photo object adapter and contract. It does not establish a placed, playable realm, accepted physical artwork, or a working cloud fax transmission. Claude owns realm layout, native placement and live Play acceptance; Blender owns physical object art subject to explicit acceptance. The scoped Codex implementation owns the existing-app bridge. No arcade, Dungeon Master, tactics, audio, shared editor, or shared art files are changed.

## First pilot

`ADaedalusPhotoPdfMachine` uses the existing `ADaedalusUsable` / Hero `Interact` seam. A local user pairs it at runtime with the opt-in PhotosToPDFPC companion link. Interacting opens that same app's local chooser, where the user explicitly selects images, converts them, and downloads the generated PDFs. The browser and original desktop interface use the same PDFBox conversion primitive. The adapter's state describes pairing and launching only; a browser launch cannot prove conversion or delivery.

The source converter makes **one image-sized, single-page PDF per photo**. This pilot preserves that behavior. It does not merge photos into a multi-page document, scan a folder, invoke OCR, physically print, or send a fax. Multi-page merging would be a separately disclosed enhancement.

The [photo contract and acceptance procedure](contracts/photo-pdf-v1/README.md) define boundaries, pairing and evidence. The bridge binds to loopback only, defaults off and never accepts client filesystem paths. Synthetic fixtures are the only test documents. Files stay on the user's PC; provider transport is not involved.

## Source-backed next candidates

These are inspected implementation candidates, not integrated products or current test certifications. Prioritize finished or nearly finished functionality; skip empty projects. Pins below are source snapshots, not automatic update instructions.

| Priority | Existing implementation | Physical interface proposal | Reuse boundary and remaining work |
|---|---|---|---|
| 1 | PhotosToPDFPC, `PhotosToPDFPC/src/main/java/com/photostopdfpc/service/PdfConversionService.java` | Scanner / PDF printer | First pilot. Original PDFBox service reused; one PDF per image. Local bridge, native adapter, artwork/Play acceptance tracked independently. |
| Explicit exception | fax-trident desktop + Spring server | Fax machine | Existing `sendFax` counted PDF pages and labeled them sent without transport; controller also returned a different ID. Transport implementation is required. Default-disabled real provider adapter and local mock tests are separate from actual receipt. |
| 2 | image-optimizer [`a870c16c`](https://github.com/RicheyWorks/image-optimizer/tree/a870c16ce966eeb4d993eabce5a808847e985094), `ImageOptimizer.optimizeImage`, `OptimizationPlan` | Photo workbench | Actual Thumbnailator resize/re-encode exists. Plan avoids input/output aliases, links and collisions. Reuse it; selected images only, preserve originals, expose explicit quality/format controls, add bounded job interface before realm integration. No port started. |
| 3 | synapse [`6760f4ca`](https://github.com/RicheyWorks/synapse/tree/6760f4ca5f33cda8301eaf41f017452eaea2f38c), `synapse-core/src/scheduler.rs`, `src-tauri/src/main.rs` | Study desk / memory cards | Real Rust SM-2 scheduling and Tauri `review_memory` persist to the existing local store; FSRS is another existing strategy. Adapt that command surface, preserve the personal vault and review history. Do not copy review rules into a different engine. No port started. |

Research leads awaiting this pilot's follow-up source review: public-feed reading in ZeroDayFeedParser; allowlisted, explicitly approved workflows in echoes/automaton; a concrete PNG-export biomorph sketch in ProcessingMasterArchive. SecureFileVault needs crypto/overwrite/key-handling hardening before a commercial object. Jerky's CRC/archive library is not proof of a complete backup app. Other games remain with their assigned arcade/game owners.

## Fax reliability boundary

The existing desktop fax app remains the interface. A real backend must bind recipient confirmation to an immutable document digest and owner-scoped durable job ID. Provider acceptance means queued; only verified delivery evidence means delivered. An uncertain submission must be reconciled, never blindly resent. Preparation and simulation must say so. Authenticated callbacks, bounded status reconciliation, retention and document access are required before activation. See the scoped fax-trident implementation for the actual provider contract and tests.

The intended provider path is Telnyx Programmable Fax: [send API](https://developers.telnyx.com/api-reference/programmable-fax-commands/send-a-fax), [signed webhook reception](https://developers.telnyx.com/docs/development/api-fundamentals/webhooks/receiving-webhooks). A configured provider needs an account, credentials, sender number/connection, approved public PDF-fetch/callback endpoints, and explicit cost/data authorization. This work buys nothing, creates no credentials, deploys nothing, and sends no real faxes. Mock adapter evidence cannot establish a recipient received a fax.

## Product ownership

The user intends finished apps and their physical objects to become NFT products with broad commercial reuse rights for the user's owned work. Record these separately: ownership representation; application license/access; third-party dependency and asset provenance; provider usage charges. NFT ownership does not create provider credits or transfer rights the seller does not own. This implementation changes no licenses and mints, lists, sells or deploys no tokens/contracts. Commercial license wording and entitlement verification need their own reviewed work before sale.

## Verification ledger

Record exact source commits, app and native draft PR heads, remote checks, synthetic PDF validation, and owner acknowledgments with the handoff. Portable C++ tests, real Unreal compilation and live runtime acceptance are different results. A green CI badge cannot substitute for the last two. Until Claude records placement/interaction/Play proof and Blender accepts the art brief, the physical-object integration remains awaiting live acceptance.

Local native verification for this slice: 51/51 MSVC policy checks pass, including all ports from 0 through 70,000 and all token byte values. An isolated Unreal 5.8.3 UBT build generated `DaedalusPhotoPdfMachine.generated.h` with UHT and successfully compiled the new `DaedalusPhotoPdfMachine.cpp` translation unit. The full module build is blocked by the existing `DaedalusHero.cpp:1227` C2181 error around an unbraced `else UE_LOG(...)`; the same source was verified on upstream `4447c043`. No shared-source fix, editor restart, live placement or Play test was performed by this slice. The owner was notified in hub messages 28707–28709.
