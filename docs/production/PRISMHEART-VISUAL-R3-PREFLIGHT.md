# Prismheart visual stage r3 — input and capture preparation

**Current status: r3 title recovery and both builds completed; eight supplementary UI JPEGs recorded; planned battle and late-game visual acceptance remains pending.** The completed successor build is still `11-ultra-controller-r2`. Local source checkpoint `caf1b103f6cf5a3a66a3c718c139a7091b727b9d` contains the exact 47 preserved source/document/report paths. The r4 successor DOM review surface and a separate, newly approved v10-derived four-fixture adapter are authored in source only, default OFF. Independent static review of the final adapter pin is CLEAR, with no blocking source findings. No r4 tests, builds, browser sessions or new captures have run; accepted comparison pairs remain zero.

The historical preflight below records the earlier missing-title boundary. Its statements that recovery/builds/captures had not run describe that point in time; the append-only milestones at the end record what subsequently completed. The r4 contract's earlier baseline-adapter absence likewise describes its original source-only boundary; the separate adapter milestone at the end supersedes that absence without changing the frozen v10 original or successor. Preserve the existing r3 inputs, build outputs and captures. The historical raw document SHA256 before this update was `2a1bd6066ca9146c07407161b978e71676ef7ba6ff727c2d1d90e133429e135e`.

## Historical r3 preflight — preserved point-in-time record

**Stage: INPUTS_PRESERVED_WITH_MISSING_TITLE; NOT BUILT OR CAPTURED.** The game successor remains `11-ultra-controller-r2`; “r3” names this production-preparation package, not a new gameplay release. Owner: Ultra / buckwild-sol. Actual start2026-10-15 22:04:36 UTC. Coordinator direction: hub32420; START/slot request32431; concrete missing-input report32435.

## What is ready

The current source and an exact v10 source baseline now have separate owned input roots. Existing art/audio was copied without altering its originals; each source/copy SHA-256 matched. These are file inventories, not decoded-image, build or runtime acceptance.

| Input | Location / evidence |
| --- | --- |
| Common art root | `artifacts/prismheart-visual-r3/input-art/` —595files,18,158,359bytes |
| Art inventory | `data/assets/prismheart-visual-r3-art-pins.json` —530existing1x PNGs plus10cue MP3s,54event WAVs and one cue metadata JSON; this is a source superset, not an exact packed-atlas count |
| Original engine/data/controller root | `artifacts/prismheart-visual-r3/input-source/v10/` —32files:13original demo sources plus19frozen RPG/controller/settings dependencies |
| Current engine/data/controller root | `artifacts/prismheart-visual-r3/input-source/r2/` —32files with the current reviewed source and identical frozen dependencies |
| Source inventory | `data/assets/prismheart-visual-r3-source-pins.json` |
| Title recipe reference | `artifacts/prismheart-visual-r3/title-recipe/` —five source files from exact upstream9175723 |
| Title recipe archive | `artifacts/prismheart-visual-r3/title-recipe-9175723ad.tar`,61440bytes, SHA256 `9443e6cdc3e7030843fc672a44bb1f71aa46de0b34ee72df2767a3ac60646370` |
| Shot specifications | `data/assets/prismheart-visual-r3-shot-plan.json` —four matched source comparisons and two new-content scenes; zero actual images |

The originals in D2-build, published v10, r1/r2 source archives, frozen shared controller/settings, native intake and Reedwheel are unchanged. No gameplay code was edited in this stage.

## Required missing input

Both original and current builders require **`TitleBg_1x.png`**, the menu-free8-frame320×224 title backdrop:2560×224 RGBA8. It is absent from every current builder search location and the bounded D2-build-wide filename inventory.

The existing `claude-battle-kit/prism/title/Title_1x.png` is also2560×224, but its menu/window/prompt/credit are baked in. Its SHA256 is `e5aed50faafd343037aa03e2e51bf524b01e83786ac8d56695e2829acfb19c1a`. Dimensions were read from its PNG header without image decoding. Matching dimensions do not make this the missing input: substituting it would duplicate the engine's live menu.

The other required filenames resolve under the existing kit layout:42town,11interior and37world tile references; four dungeon themes with14PNGs each;8party,136foe,5boss and34spell strips;9NPC,16menu icons and17UI strips;20backdrop references;10cue MP3s and54event WAVs. Audio output basenames do not collide. These findings establish file availability only.

Folly's sewer backdrop lives at `claude-battle-kit/prism/Backdrop_Prism_sewer_1x.png`; Brannoc's battle art is also in the kit. Its four additional foes and Colossus resolve under `claude-battle-sprites/prism/`. A general sprite override is unnecessary. Dungeon/NPC/UI/menu globs still require the retained kit directories.

## Safe title recovery boundary, not executed

First preference is the exact retained menu-free file from the published v10 artifact or its producer, with provenance and hashes. No local published v10 packed `data.json`/atlas set or gameplay screenshots were found in the bounded workspace/D2-build/bot-team searches. The published artifact is known by its handoff name, **Prismheart Playable Demo, version10**, not by a supplied local output path.

If the producer needs to regenerate that file in a later explicitly permitted slot, the exact original recipe closure is:

- `tools/blender/rpg_title.py`
- `tools/blender/pixel_png.py`
- `tools/blender/pixel_font.py`
- `tools/blender/rpg_battle_ui.py`
- `tools/blender/rpg_menus.py`

The background-only path needs NumPy and standard library. It does not need Blender, Pillow, party sprites or RPG JSON. The narrow operation is original `title_backdrop("prism", frame)` for frames0–7, concatenate horizontally, then original PNG writer once into a **new owned output**. No import or generator execution occurred here.

Do not invoke the original `build()`/CLI blindly: it produces both realms and multiple images; supplying `data_root` also overwrites `data/rpg/title.json`. The original PNG writer uses `wb`, so any later wrapper must reject an existing destination and preserve uncertain prior output. Imports modify `sys.path` and perform a static font assertion; they have not been executed in this stage.

Keep the recovered file directly at the root of a new title-only overlay, separate from the595frozen inputs: `<TITLE_ONLY_OVERLAY>/TitleBg_1x.png`. Pin its actual source, bytes, SHA256, dimensions and production receipt. Both future builds must use the same overlay. No placeholder, rename or fabricated image was added.

## Future build shape and authorization

No applicable Ultra build/browser/render slot has arrived. Native release32424 and Opus's different cloud-stage grant32427 do not allocate this job. No expired grant is reused. Request32431 remains pending; missing-title request32435 asks for the exact file or a permitted narrow recovery.

Prepared command shapes below are **unexecuted**. `<TITLE_ONLY_OVERLAY>` must be a real, newly pinned directory containing the recovered `TitleBg_1x.png`. Outputs must be absent/versioned before any later permitted execution. Runtime/dependency availability has not been probed by imports.

```powershell
python artifacts/prismheart-visual-r3/input-source/v10/tools/rpg_demo/build_demo.py artifacts/prismheart-visual-r3/input-art artifacts/prismheart-visual-r3/build-v10-reconstruction --sprites "<TITLE_ONLY_OVERLAY>"
python artifacts/prismheart-visual-r3/input-source/r2/tools/rpg_demo/build_demo.py artifacts/prismheart-visual-r3/input-art artifacts/prismheart-visual-r3/build-r2 --sprites "<TITLE_ONLY_OVERLAY>" --source-root artifacts/prismheart-visual-r3/input-source/r2
```

Run a later permitted stage one process at a time. The v10 builder reads its own copied repository root; the r2 builder can use the explicit source root. Do not run preserved test scripts as part of this proposed build/capture scope. A future runtime acceptance scope must be explicit.

## Comparison labels and capture limits

A rebuilt baseline must be labeled **“v10 source reconstruction on common pinned art.”** It is not a recovered screenshot of the published v10 artifact. Use identical common data/art/controller/settings hashes, with distinct pinned engine/builder sources. Match browser/font setup, viewport, DPR, integer scale and saved fixture for each pair.

The shot plan targets1280×896 at4× the320×224 canvas, DPR1, subject to actual permitted browser capability. Record actual settings rather than assuming them. The four pairs cover party HUD readability, landed Drowse, landed Lull and Gust. The two new scenes cover Folly/Colossus and Brannoc's Inn calibration. They have no playable v10 equivalents and must be labeled **new content**, not before/after improvements.

FX timing remains a capture prerequisite: current public state hooks expose neither spell age nor `statusLanded`. Intended0.325s/0.455s targets need later approved observed timing control. A fixed wait or `speed(0)` alone does not freeze cursor/tile performance clocks or draw-based flash decay. No capture framework or new hook was written.

Staged scenes using existing hooks must be labeled staged. Screenshots cannot establish frame rate, controller feel, accessibility, save/reload, reward limits, networking, native fidelity or NFT/token sale readiness. Settings pause needs actual state observation across a permitted interval, not one still image.

## Current result and lessons

This stage preserves inputs and makes the next production job concrete. It contains **zero builds, tests, syntax checks, imports, browser sessions, captures, renders, Blender/native calls or publications**. No quality pass or runtime success is claimed.

A title file with the same dimensions can still be semantically wrong. Resolve build inputs before taking a scarce execution slot. Preserve exact source and common art for comparisons, distinguish a source reconstruction from a published artifact, and keep new-feature evidence separate from matched visual changes. Retain the pixel JRPG genre rather than importing another realm's art expectations.

## Subsequent r3 execution milestone — actual retained evidence

The earlier missing-title and unexecuted-build status was superseded by grant32445 and handoff32450/32451. `artifacts/prismheart-visual-r3/execution/visual-execution-report.json`, reported2026-10-15 22:36:05 UTC, records **three successful sequential production processes**: one original-recipe title recovery and two Pillow builds. Each used one CPU affinity mask1 and exited successfully; the individual terminal/release receipts record release of the owned compute phase. These three production processes do not count the later temporary preview server as a production build.

| Completed output | Retained evidence |
| --- | --- |
| Original menu-free title recovery | `artifacts/prismheart-visual-r3/title-recovery-r1/recovery-receipt.json`; `TitleBg_1x.png` is12,609bytes,2560×224 RGBA8, SHA256 `2f1402fb85619ca96fceb7269a323043a8a20e89ff2b1a87577b39b498d35446` |
| Baseline reconstruction | `artifacts/prismheart-visual-r3/build-v10-reconstruction/`;75files; label **v10 source reconstruction on common pinned art**, not the recovered published v10 artifact |
| Reviewed successor build | `artifacts/prismheart-visual-r3/build-r2/`;75files; built r2 engine SHA256 `0c4ed03f9c66b38df28eaae45205e82de8b11bac002a2168ada01e526c91220f` |
| Exact output inventories | `artifacts/prismheart-visual-r3/execution/build-output-inventory.json` |
| Process and release receipts | `execution/recovery-process.json`, `execution/build-v10-reconstruction-process.json`, `execution/build-r2-process.json` and the corresponding `*-terminal-release.json` files beneath the r3 root |

Both builds contain the same recovered title SHA above. Its recovery receipt's original `PENDING` acceptance fields are historical; the later execution report records only the limited observed views described next, not a completed combat or gameplay acceptance.

Eight supplementary JPEGs were captured through supported browser UI operations in `artifacts/prismheart-visual-r3/execution/captures/`:

| Observed view | Baseline reconstruction JPEG | r2 JPEG |
| --- | --- | --- |
| Title menu | `v10-reconstruction-title.jpg` | `r2-title.jpg` |
| Name entry, `ABCDEFGHI`, cursor A | `v10-reconstruction-name-entry.jpg` | `r2-name-entry.jpg` |
| First opening Town dialogue page, revealed | `v10-reconstruction-opening-dialogue.jpg` | `r2-opening-dialogue.jpg` |
| Opening field menu, ITEM selected | `v10-reconstruction-opening-field-menu.jpg` | `r2-opening-field-menu.jpg` |

The execution report records1280×896 viewport, DPR1 and a4× display of the320×224 canvas. It pins every JPEG's actual bytes and SHA256. Inputs were ordinary canvas keyboard events; no `PRISM_DEMO` state mutation or serialized save fixture was used. Animation timing was not frozen or measured, so title-frame or spell-phase equivalence is not claimed. The field-menu JPEGs have identical recorded hashes; that observation does not establish the planned battle-HUD comparison. The report also records the corrected locator/non-editable-canvas staging errors rather than omitting them.

The four planned battle comparisons (`party-hud-command`, `drowse-landed`, `lull-landed`, `fennick-gust`) and two new-content scenes (`folly`, `workshop`) remain `PENDING_UNCAPTURED`. The eight supplementary JPEGs do not replace them. Controller-device recovery, pause recovery, save/reload, reward limits, gameplay end-to-end, test suites, Blender/native actions and publication remain unaccepted. The owned review tabs were closed, the temporary viewport reset, and the preview-server receipt records the owned PID terminated with its port no longer listening.

## Local source checkpoint milestone — exact47, no push

The later `artifacts/prismheart-visual-r3/execution/checkpoint-direct-human-commit-attempt.json` records local commit **`caf1b103f6cf5a3a66a3c718c139a7091b727b9d`** on existing branch `main`, parent `c1ce262d74ad01e3e0ecd36fb8f3d52e57a1ef4c`, at2026-10-15 23:20:37 UTC. Its exact47 committed paths cover owned Prismheart/controller/title-recovery sources, documents and JSON reports. The receipt records zero remaining staged paths and all seven unrelated tracked working files preserved byte-for-byte. No push or branch switch occurred; runtime outputs and binary assets remain outside that source commit.

`execution/checkpoint-direct-human-commit.stdout.txt` retains the actual Git output. `execution/checkpoint-index-verification.json` distinguishes27 exact raw-byte files from20 JSON files normalized only from CRLF to LF in Git. Historical raw SHA records and normalized Git-blob identities must remain distinct. The execution report's earlier main-commit approval-pending boundary is superseded by this later successful commit receipt; the earlier report is not rewritten. This documentation continuation and the authored r4 engine changes are later work, not claimed as contents of `caf1b103`.

## r4 app-owned DOM review contract — source only, default OFF

**Historical source boundary:** this section records the successor's first r4 source freeze, before separate adapter approval. Its baseline-adapter absence is superseded by the later v10-derived adapter milestone below; its recorded source and execution facts are preserved.

The r4 continuation addresses the remaining inability to stage and observe exact review fixtures through supported application UI. The authored source in `tools/rpg_demo/index.html`, from `reviewAssert` through `mountVisualReview`, provides a visibly identified, app-owned DOM surface, explicitly enabled only by **`?visualReview=r4`** and **OFF by default**. The final source candidate is 137,603 bytes, SHA256 `12a6dc5f96d107c52c592fd4c992ca3441ba9762cf9bc9b61c16507acff971da`. It is intended for a new disposable review page. Source preparation is not permission to run a new build, server, browser session or capture. The existing r3 builds remain their recorded v10 reconstruction/r2 versions; neither has been replaced with this r4 source.

The review panel is below the normal viewport-height canvas. Six ordinary buttons carry `data-review-fixture` attributes:

| Attribute value | Staged scene / existing shot-plan relationship |
| --- | --- |
| `hud-readability` | Party HUD command scene; four Gelfins, nine-letter lead name, low HP/MP, a KO and status tags; corresponds to planned `party-hud-command` |
| `drowse-landed` | Actual Drowse action; corresponds to planned Drowse view, subject to the selected cast condition |
| `lull-landed` | Actual Lull action; corresponds to planned Lull view, subject to the selected cast condition |
| `gust` | Fennick's actual Gust action against the Pyre Warden; corresponds to planned `fennick-gust` |
| `folly` | Staged optional Folly route; successor-only new content |
| `workshop` | Staged post-Folly Brannoc reading at the Inn; successor-only new content, not a completed drill |

The remaining controls are native labeled DOM elements:

| Element | Source contract |
| --- | --- |
| `#review-cast-variant` | Select `cast` (fresh target), `recast` (already affected target) or `immune` (Drowse against an immune Warden only). Lull with `immune` reports unsupported; Gust uses its own fresh-cast fixture. |
| `#review-fx-age` and `#review-apply-age` | Numeric age 0–0.649 seconds, step 0.001; apply the age to the existing staged spell. Initial Drowse/Lull age is 0.325 seconds and Gust 0.455 seconds. Apply is disabled without a spell or after a fatal unsupported fixture. Invalid input records a separate `controlError`, preserves the frozen scene, and can be corrected and applied again. |
| `#review-workshop-runs` | Select staged completed-run count 0, 1 or 2 to show the pressure, timing or heat reading respectively. The normal drill's answers and rewards remain disabled in review. |
| `#review-folly-boss` | Show the actual optional Colossus encounter as successor-only new content. |
| `#review-show-canvas` | Scroll back to the staged canvas using an ordinary button; publish a fresh pending-draw state and await the subsequent actual draw. |
| `#review-leave` | Remove the `visualReview` query parameter and reload normal play. Review enablement is not stored in a save or Settings. |

`#review-record` is an `<output>` containing JSON under schema `daedalus.prismheart.review-state/v1`. Its DOM attributes expose `data-fixture`, `data-status`, `data-phase`, `data-fx-age`, `data-status-landed` and `data-rendered`. The JSON records actual staged party/encounter/field state, spell age and atlas frame, whether this cast landed a status, whether that status is currently present, target survival, pop ages, flash state, staged flags, geometry and unsupported reasons. These are staged inputs to the real source, not proof of campaign progression or a saved journey.

Selection or age application first clears the rendered marker. Resize calls `fit()` and invalidates that marker; passive scroll likewise refreshes the recorded canvas geometry and awaits a new draw. The animation-frame callback draws once per pending request, sets `rendered` only after that actual draw, then republishes the record; it does not continuously redraw the frozen scene. Unsupported scenes retain `data-rendered="false"`. A future browser pass must observe **`status: "STAGED_SOURCE_STATE"`**, the desired fixture, exact spell age and result, `controlError: null`, `data-rendered="true"` and the actual visible canvas geometry after scrolling or resizing. The initial title can be rendered with no fixture selected, so the rendered marker alone is insufficient. The record's viewport, DPR, native 320×224 dimensions, canvas CSS bounds and scale must agree with the observed geometry for that capture; the source does not assume that merely choosing a fixture produces 1280×896 at 4×.

Spell fixtures call the existing `doAction` resolution with the isolated closure-scoped Mulberry32 seed `0x92D4860B`, recording its draw count. They do not replace global `Math.random`. A requested success/recast/immunity condition that does not match the real result reports unsupported rather than overwriting the result. Success symbols still require both the actual `statusLanded` result and a living target with that status. Review time is explicit; simulation ticks, reward resolution and campaign callbacks are stopped, and the render clock and draw-based flash handling are frozen for this review branch.

The review contract preserves the existing pixel JRPG, party, inventory, story, saves and shared controller/settings contract. The source suppresses review-page save reads/writes, audio, shared controller/settings instances and the normal `PRISM_DEMO` harness exposure. Workshop choices are displayed without advancing them. Fixture selection and timing controls must be explicit app UI actions; browser tooling must not bypass that surface through arbitrary application-state evaluation. Normal play remains the source branch selected when the review query is absent.

A later separately permitted capture pass must retain engine/build hashes, common art/data/controller/settings pins, viewport/DPR/scale, selected fixture and actual observable timing. Baseline reconstruction versus successor comparisons and successor-only Folly/workshop scenes retain the labels above. **No baseline DOM adapter has been authored.** Preserved v10 cannot yet select these exact review fixtures through an equivalent app-owned surface. The four matched current-versus-v10 comparisons therefore remain unsupported until a separately reviewed baseline adapter exists; current r4 fixture controls alone do not complete them. Folly/workshop remain new content with no playable v10 equivalents. A missing baseline surface or timing capability must not be replaced by an unmarked simulated before image.

For this r4 source continuation: **tests, syntax/runtime checks, builds, servers, browser sessions and new captures are all UNRUN**. No existing r3 output was regenerated, no new runtime acceptance is inferred, and no native, blockchain, sale or external publication step is included.

## Separate v10-derived review adapter milestone — authored, unexecuted

Specific user approval at 2026-10-16 00:07 UTC permits four adapter/staging/documentation source files, with no builds, captures or commits. The retained approval evidence is `C:/Users/730ri/Documents/Codex/2026-10-14/task/ultra-v10-source-approval-20261016T0007Z.txt`. This milestone is **AUTHORED_UNEXECUTED**. It supersedes only the earlier absence of a baseline review surface; no comparison pair is accepted.

The separate owned adapter is `artifacts/prismheart-visual-r4/review-adapter-v10-r1/index.html`. Its frozen source is 122,652 bytes, SHA256 `9f7bb33dd87ff34cc3530755bc7da3993d60399cfbf5f5d80cbee55e82fe7930`. Closing independent static review of this exact pin is **CLEAR**, with no blocking source findings. This is source review, not runtime or visual acceptance. Companion provenance belongs in `artifacts/prismheart-visual-r4/review-adapter-v10-r1/adapter-manifest.json` and the shared `data/assets/prismheart-visual-r4-staging.json`. Those files describe source capability, not observed browser results.

The adapter derives from the preserved v10 source at revision `9175723ad200b05558a2ea12470763c3b9432152`: `artifacts/source-snapshots/prismheart-v10-source/tools/rpg_demo/index.html`, 107,990 bytes, SHA256 `5114a5aedfe414a29894e642a2cc0bd48078160f4cb3ba1b9bffa82358aaec0b`. Its label is **v10-derived review adapter on common pinned art**, a source reconstruction rather than the published v10 artifact. The frozen original and the successor engine at SHA256 `12a6dc5f96d107c52c592fd4c992ca3441ba9762cf9bc9b61c16507acff971da` are retained without edits from this adapter work.

The adapter enables its panel only through the same explicit **`?visualReview=r4`** query. It offers exactly four `data-review-fixture` buttons: `hud-readability`, `drowse-landed`, `lull-landed` and `gust`. The HUD fixture uses the same four jobs, nine-letter lead name, four Gelfins, low HP/MP, KO and status inputs as the successor staging contract. The source retains the original v10 HUD layout, plain-text status rendering, draw order and atlas-only spell effects. It does not import the successor's status pills or bespoke effects.

The common controls are `#review-cast-variant` (`cast`, `recast`, or Drowse-only `immune`), `#review-fx-age`, `#review-apply-age`, `#review-show-canvas` and `#review-leave`. Age is 0–0.649 seconds in 0.001 steps, initially 0.325 for Drowse/Lull and 0.455 for Gust. Gust always uses its fresh-cast fixture; Lull immunity reports unsupported. Invalid age input records `controlError` while preserving the previous frozen state and allowing a valid retry. Leave removes the query and reloads the derived page's normal v10 branch. No Folly or workshop button, route, boss or dialogue is inserted into this baseline; both remain explicitly unsupported and successor-only new content.

Spell staging invokes the real v10 `doAction` branch with the same isolated closure-scoped Mulberry32 seed `0x92D4860B`; global `Math.random` is not replaced. The native v10 `B.fx` structure stays unchanged. A separate review observer records the original status branch's local `ok` result in `castResult`. The DOM record discloses that provenance through `spell.statusLandedBasis` and `nativeStatusLandedField: false`. Gust has no status-resolution result, so its observed `statusLanded` is null and its DOM attribute is `not-applicable`; it is not fabricated as a native false flag. Recast or immunity results are checked against the actual resolution, with a mismatch reported unsupported.

The adapter uses the common `#review-record` schema and capture gate: `status: "STAGED_SOURCE_STATE"`, desired fixture/view, `controlError: null`, `data-rendered="true"`, exact age and cast result, and current visible canvas geometry. A pending request draws once before publishing the rendered marker. Scroll or resize invalidates and refreshes that evidence; the initial rendered title with no fixture selected does not satisfy the gate. Review mode suppresses native campaign ticks, queues, rewards, saves, audio, controller/settings instances and the normal public harness. These are source guards, not runtime acceptance.

Its `<base href="../../prismheart-visual-r3/build-v10-reconstruction/">` deliberately binds scripts, data and images to the existing preserved v10 reconstruction. A later separately authorized browser/server allocation must serve a common ancestor of both artifact directories and keep this relative layout intact. Serving only the adapter directory would not supply those sibling assets. No new baseline build or writer is needed for this in-place source arrangement, and none is authored here. Relocation or repackaging needs its own explicit plan and authorization.

The preserved r3 `build-r2` predates the successor's r4 DOM panel and cannot act as its review page. A future approved successor build must use the exact pinned current engine together with frozen r2 data/controller/settings, common art and the recovered title overlay. The existing `tools/rpg_demo/build_demo.py` copies its `index.html` from its own `HERE` directory; `--source-root` selects data/dependencies, not an alternate engine. Its source therefore supports a current-engine build with the frozen r2 source root, subject to a fresh output and an explicit production allocation. No new builder/helper or deployment is authored in this adapter milestone, and this source approval grants no build or server slot.

The two versions share pinned canonical inputs, but their packed data and atlases retain distinct versioned identities. Future comparison evidence must retain each actual loaded source/build hash, assets/base binding, geometry and DOM record alongside two actual images. Four common source controls now exist; matched visual acceptance still awaits a separately permitted run of both sides. Folly/workshop never acquire a fabricated v10 before image. **Adapter imports, syntax checks, tests, builds, servers, browser sessions, fixture runs, new captures, accepted pairs, compute and Git mutations are all UNRUN in this source-only milestone.**

## Ultra lessons-review checkpoint — 2026-10-15 Pacific

Owner: **Ultra / buckwild-sol**. This append responds to all-team review 32641
(opened 2026-10-16 01:21 UTC); participation ACK 32659 was delivered and read back
in the established `pootscoot-coordination` hub. The three attributed lessons are
in `docs/LESSONS-LEARNED.md`, section **Ultra — Prismheart production review
(2026-10-15 Pacific)**: semantic asset identity, observable review state, and
separate allocation/execution/acceptance receipts. Each includes pinned evidence,
reproducible settings, observed results, remaining gaps, estimated benefit/effort,
existing owners and the next permitted step. Pootscoot owns consolidation into
the existing Whole workflow harness backlog; this contribution does not edit
that coordinator-owned block or create another tracker.

Current status remains **SOURCE COMPLETE; EXECUTION HELD**. The reviewed r4
current engine SHA256 is
`12a6dc5f96d107c52c592fd4c992ca3441ba9762cf9bc9b61c16507acff971da`;
the separate v10-derived adapter is
`9f7bb33dd87ff34cc3530755bc7da3993d60399cfbf5f5d80cbee55e82fe7930`,
its manifest is
`7bad8400ef3c2a48ef81bb8117316582a330c0a71ace7c61a358993d95cabb3d`,
and staging metadata is
`388ed54787272f8106740a80f14f0aaa970a5e85dc44f71088b804e88b16c057`.
The r3 report's three successful processes/eight supplementary UI JPEGs are
historical completed work; its six planned battle/new-content scene entries are
still pending. R4 has zero fixture runs, new images or accepted pairs. Its
`build-current-r1` and execution directory are absent at this checkpoint.
Request 32631 remains held for fresh resources/allocation; this review starts
no claim, build, browser/server, capture or native operation. Native custody
remains solely codex-play-guard regardless of lock TTL.

Both documentation additions preserve their full prior byte prefixes, all other
authors and frozen source/delivery/intake bytes. This handoff's earlier hashes
identify historical versions and are not silently repinned; current appended
document hashes are reported separately through the hub. No tests, source edits,
commits or new runtime/visual acceptance accompany this review.

## Ultra capture contract r1 — file-only continuation, 2026-10-15 Pacific

Owner: **Ultra / buckwild-sol**. This is the single resumed preparation requested
after the user's computer update and credit confirmation (parent continuation,
2026-10-16 04:56 UTC). Actual preparation START was delivered as hub 32731.
A bounded search of the existing r4 execution folder and this owned handoff found
no partial 17-view checklist. This append supplies it in the existing handoff;
there is no duplicate source assignment, new tracker or capture framework.
**Stage: CONTRACT PREPARED; BROWSER RUNTIME UNQUALIFIED; ALLOCATION PENDING.**
The completed offline build is retained; neither it nor the 734-input/75-output
reviews are rerun here. The earlier source-only and absent-output statements
above remain dated historical milestones, superseded by the build receipts below.

### Exact page and provenance bindings

Serve the existing common ancestor `C:/Users/730ri/projects/Daedalus2/artifacts`.
The two relative request paths are source-derived, not live URLs:

- **C (current):** `prismheart-visual-r4/build-current-r1/index.html?visualReview=r4`.
  The actual built index is 137,603 bytes, SHA256
  `12a6dc5f96d107c52c592fd4c992ca3441ba9762cf9bc9b61c16507acff971da`,
  identical to `tools/rpg_demo/index.html`. Its packed `data.json` is 356,759
  bytes, SHA256 `b7d2b7837fed99cc1979d5ad673a2989a9a78091e6ac5d8d81625ca97b3fbefd`.
  Label **current r4 review on 11-ultra-controller-r2 data; staged scene**.
- **B (baseline):** `prismheart-visual-r4/review-adapter-v10-r1/index.html?visualReview=r4`.
  The adapter is 122,652 bytes, SHA256
  `9f7bb33dd87ff34cc3530755bc7da3993d60399cfbf5f5d80cbee55e82fe7930`.
  Its literal `<base href="../../prismheart-visual-r3/build-v10-reconstruction/">`
  must resolve to the preserved v10 reconstruction, whose packed `data.json` is
  323,981 bytes, SHA256
  `941e710bba52ad293100ba732caa39683a1371900bcb98278fa77109450c12a7`.
  Label **v10-derived review adapter on common pinned art; reconstructed source,
  not the published v10 artifact**. Keep its original HUD, text statuses, draw
  order and atlas-only FX; it has no Folly/workshop playable equivalent.

Retained bindings, narrowly re-read for this preparation:

| Existing file | SHA256 |
| --- | --- |
| `data/assets/prismheart-visual-r4-staging.json` | `388ed54787272f8106740a80f14f0aaa970a5e85dc44f71088b804e88b16c057` |
| `artifacts/prismheart-visual-r4/review-adapter-v10-r1/adapter-manifest.json` | `7bad8400ef3c2a48ef81bb8117316582a330c0a71ace7c61a358993d95cabb3d` |
| `artifacts/prismheart-visual-r4/execution/build-current-r1-output-inventory.json` | `47019c7155de5528fa1b08a3f7705c35e777796bad98b2d1c617aeff55ba398f` |
| `artifacts/prismheart-visual-r4/execution/build-current-r1-execution-report.json` | `b8832f04ae90db6a562a84234776044f6ff9b5f93467a03388d82194e3e22942` |
| `artifacts/prismheart-visual-r3/execution/build-output-inventory.json` (baseline root entry) | `b1f0fbacf8934c79ab22f8cd1ad174f56240cc9b3cbb2d3ff4e3f32d03d45b28` |

Root's independent file-stage CLEAR is hub 32720. The current output has 75 files /
18,775,956 bytes; the preserved baseline has 75 files / 18,704,626 bytes. These
retained inventory results are not a fresh full audit or runtime acceptance.
The original source/art/title/dependency manifests stay unchanged. Current
packed data differs from retained r2 only in `zones` object-key order, as recorded
by the completed build review; do not rebuild or normalize it for byte parity.

### Existing controls and common capture gate

Use only the visible app-owned panel enabled by the exact query above. The
fixture selector notation in the table means an actual button
`#visual-review [data-review-fixture="ID"]`, not a hidden function call.
Set `#review-cast-variant` to the table value through its native select control.
Selecting Drowse/Lull reads that value; changing it reloads an already selected
status fixture. Gust always stages `cast`. For spells, explicitly enter the
listed age in `#review-fx-age`, click `#review-apply-age`, and inspect the actual
result. Valid ages are 0–0.649 seconds in 0.001 steps. Use
`#review-workshop-runs` value `0` for the one workshop view. No choices/answers
are enabled. `#review-folly-boss` selects the actual Folly boss fixture.

Both pages reset the four staged jobs to Bladeward, Beastcaller, Chronoseer and
Lightmender at level 15; lead name `ABCDEFGHI`. HUD expectations are the existing
staging JSON's exact numeric party rows, poison/KO/protect states and four Gelfins.
Status casts use Quill/Chronoseer; Gust uses Fennick/Beastcaller. The existing
isolated Mulberry32 seed is `0x92D4860B`; global `Math.random` is not replaced.
Inputs in this contract are source expectations, not observed browser outcomes.

For every row, read actual `#review-record` text and attributes via a supported
browser DOM observation surface. Require schema
`daedalus.prismheart.review-state/v1`, desired fixture and exact table `view`,
`status: STAGED_SOURCE_STATE`, `unsupportedReason: null`, `controlError: null`,
`frozen: true`, `simulationTicking: false`, `saveWritesAllowed: false`,
`rewardsResolved: false` and `data-rendered="true"` after the pending draw.
The record's `rendered.fixture`, mode/clock/spell age must agree with its current
state. A rendered startup title with fixture null does not pass. A baseline
record additionally needs the actual `assets.base` bound to its preserved
reconstruction and `spell.statusLandedBasis`/`nativeStatusLandedField: false`
where applicable. Do not require the current native FX schema on baseline FX.

**Identical view settings:** same supported browser/session family, font state,
viewport 1280 by 896, DPR 1, native canvas 320 by 224, actual CSS canvas 1280 by
896 and integer scale 4 on both sides; review touch overlay remains off. These
are requested settings, not observations. Record the actual viewport, DPR,
canvas bounds, scale, font/capability information and browser identity. If the
supported tool cannot establish and observe the same settings, report that
comparison unsupported; do not silently resize images or patch styles/state.
The source's declared fonts are Pixelify Sans and IBM Plex Mono with fallbacks;
record actual availability, without installing fonts or changing settings.

Interact with controls, then use `#review-show-canvas` to scroll the staged
canvas into view. Selection/age/scroll/resize invalidates the rendered marker;
observe its new post-draw record after the final scroll. Read the offscreen
record through supported DOM inspection without scrolling back to it. Save the
actual canvas image and raw state, then read the record again to ensure fixture,
age/result and geometry remained stable across capture. Save both readings.
If capture tooling scrolls/resizes or the state changes, label the image unpaired
and return a partial outcome; no fabricated or silently retimed comparison.

### Exactly 17 planned image/state records

Each ID below maps to one future JPEG and its raw DOM/state receipt. Rows 01–08
are the **four primary fixture comparison pairs**. Rows 09–14 are three paired
result-condition checks. Rows 15–17 are **current-only new content**, with no
baseline image or before/after claim. All rows are currently UNRUN.

| ID / filename stem | Page | Fixture | Actual record `view` | Select/input | Required source-defined result beyond common gate |
| --- | --- | --- | --- | --- | --- |
| `01-b-hud` | B | `hud-readability` | `route` | fixture button; no age | battle/cmd, clock 0, spell null, four Gelfins, exact HUD party rows |
| `02-c-hud` | C | `hud-readability` | `route` | same | same native inputs; inspect current HUD separately |
| `03-b-drowse-cast` | B | `drowse-landed` | `cast` | variant `cast`; age `0.325` | sleep landed true, active true, living target0; frame 5, clock 325, RNG draws 1 |
| `04-c-drowse-cast` | C | `drowse-landed` | `cast` | same | same actual result/age, with current native status flag |
| `05-b-lull-cast` | B | `lull-landed` | `cast` | variant `cast`; age `0.325` | slow landed true, active true, living target0; frame 5, clock 325, RNG draws 1 |
| `06-c-lull-cast` | C | `lull-landed` | `cast` | same | same actual result/age |
| `07-b-gust` | B | `gust` | `cast` | fixture button; age `0.455` | surviving PyreWarden; frame 7, clock 455; status null/landed null, DOM `not-applicable` |
| `08-c-gust` | C | `gust` | `cast` | same | same living-target damage fixture/age; status null/landed false is non-status, not damage failure |
| `09-b-drowse-recast` | B | `drowse-landed` | `recast` | variant `recast`; age `0.325` | four Gelfins; target0 already asleep; landed false/active true; `MISS`, RNG draws 0 |
| `10-c-drowse-recast` | C | `drowse-landed` | `recast` | same | same result/age |
| `11-b-drowse-immune` | B | `drowse-landed` | `immune` | variant `immune`; age `0.325` | PyreWarden; landed false/active false; `IMMUNE`, RNG draws 1; living target |
| `12-c-drowse-immune` | C | `drowse-landed` | `immune` | same | same result/age |
| `13-b-lull-recast` | B | `lull-landed` | `recast` | variant `recast`; age `0.325` | four Gelfins; target0 already slowed; landed false/active true; `MISS`, RNG draws 0 |
| `14-c-lull-recast` | C | `lull-landed` | `recast` | same | same result/age; Lull immunity is unsupported and is not a planned view |
| `15-c-folly-route` | C | `folly` | `route` | fixture button | field; actual dungeon index 4/floor 0/stairs entry (4,10), facing down; staged shard prerequisites |
| `16-c-folly-boss` | C | `folly` | `boss` | `#review-folly-boss` | battle/cmd; actual ClockworkColossus; floor 2/stairs entry (5,22), facing down; no invented gate/boss coordinate |
| `17-c-workshop-0` | C | `workshop` | `route` | runs `0`, then workshop fixture | actual Inn player (11,7)/up, Brannoc (11,6); `workshop.stagedCompletedRuns: 0`, reading fully revealed, choices VENT/STOKE, answers disabled |

The workshop's actual first reading is
`READING 1/3: THE RED GAUGE CLIMBS. STEAM HAS NO EXIT.` This stages a reading only;
no drill is answered/completed, reward resolved or save written. Folly/workshop
use disposable staged prerequisites and must stay visibly labelled new content.
The baseline canonical JSON's historical definitions do not add a playable
route, boss or workshop to its packed package.

One retained source-metadata caveat: the current engine's `baselineSupport`
string still says that preserved v10 has no review DOM adapter. That sentence
predates the separate adapter. Preserve the raw DOM record unchanged and attach
the later adapter path/hash/manifest provenance above; do not infer adapter
absence from the stale string, edit the engine, or relabel a screenshot as the
published v10 artifact during this preparation.

### Future output paths and finite run receipts (not created now)

Use the absent, versioned owned directory
`artifacts/prismheart-visual-r4/execution/capture-r1/`; it was absent at this
file-only checkpoint. Recheck absence before a later allocated run. If any
partial run is present, preserve it and seek coordinator reconciliation rather
than overwrite/replay it. For each table ID, write:

- `images/<ID>.jpg`: actual supported-tool canvas capture only; record bytes,
  SHA256, actual encoding, size, crop/geometry, capture time and source/page pin.
- `states/<ID>.json`: raw pre/post `#review-record` readings and attributes,
  actual observed page URL, browser/tool, loaded source/data/base provenance,
  viewport/DPR/geometry/age/result and the referenced image path/hash. Separate
  contract expectations from actual observations; preserve unsupported/error text.

Retain the fresh grant/deadlines, actual server executable/argv/PID/start/port,
lease claim/readback, memory/process/pin guards, server terminal/owned cleanup,
post-release locks, and image/state inventory in the same run directory as
`grant.json`, `preflight.json`, `lease.json`, `server-started.json`,
`server-terminal-release.json`, `capture-inventory.json` and `capture-report.json`.
Record actual tab identities/cleanup and previous viewport restoration where
supported. `capture-report.json` must state primary pairs accepted versus partial,
conditional pairs, current-only views and exact remaining gaps; planned 17 is
not completed 17. No files, receipts or capture outcomes exist there yet.

### One-stage request and exact present blocker

**Existing proposed producer, UNRUN:**

```text
C:\Users\730ri\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -u -m http.server 0 --bind 127.0.0.1 --directory C:\Users\730ri\projects\Daedalus2\artifacts
```

This is the existing standard-library producer used in the prior retained
preview-server receipt, with the common artifacts ancestor as its root. Retain
its executable pin `b847bb9f4e48c19f585c8bf7d8b355f3f8c6d2125717ece9c9d7e16fb9f09de8`.
A future allocated run may start at most one owned hidden ephemeral server and
two temporary supported browser tabs. Discover the actual bound port from that
owned process's output; only then form the actual loopback origin and append
the exact relative page paths above. The prior port 51482 is historical and
must not be reused as a claim of a live server. No live URL is guessed here.

Actual enabled-tool inspection in this resumed turn returned callable
`mcp__node_repl__js` (`typeof` function), plus its module-directory and reset
helpers. This proves the JavaScript tool exists; it does **not** prove a browser
client/module/session, DOM read API, viewport control or canvas screenshot API
is operational. No browser controller appears in that dynamic tool metadata
and none has returned a session/API document in this preparation. The older
`cua_repl` surface described in conversation has not been requalified after the
update. The installed Computer Use skill documents Windows `@oai/sky` window
APIs; that documentation is not a returned browser DOM capability. No tool call
initialized a node/browser runtime, imported a browser package or inspected UI.
Therefore **supported browser DOM/capture runtime remains UNQUALIFIED**, not
"node_repl absent" and not a claim of browser readiness. Do not invent API calls,
install a runtime, substitute shell/OS screenshots or treat an open-in-Codex tab
as observation evidence.

Request one later bounded allocation for supported browser qualification followed,
only if it succeeds, by this 17-view pass. Qualification must return the actual
supported browser/session documentation for visible controls, DOM record reads,
viewport/DPR and capture saving before UI methods are selected. If that surface
is absent or cannot save the required actual records/images, stop and report
the exact missing capability; no fallback source writer or UI bypass.

A fresh coordinator window and resource guards are also required: own exclusive
compute claim/readback, unchanged physical 1,700,000 / virtual 2,200,000 KiB floors,
known producer outcomes and native recovery priority. A missing/expired lock does
not transfer codex-play-guard custody or allocate this stage. The current native
restart/handshake is solely that owner's lane; no native call or second editor
launch is part of this contract. The old build grant is consumed. No lease,
server, browser, capture, renderer, test, heavy process, rebuild, Git operation,
installation, settings change or production adoption ran for this preparation.
Glorp remains cancelled and Dungeon build/adoption remains held.
