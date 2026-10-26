# Realm dependency reconciliation — 26 October 2026

The selected Gallery, Bricks and Parcels tranches are on main. They do not need
the blanket “31-commit dependency” replay. This is a source reconciliation at
main `642f75275f8f1907331a92e6746f72ec37fa367a`, not native acceptance or a new
gameplay assignment. Unreal Epic Boss retains source integration. Native work
requires the currently verified sole editor custodian; this snapshot grants no
custody. Current editor, ingestion and heavy-job holds still apply.

## Verified integration

The original saved source range is
`b684100d8ac725e10cb6d23290e6a119989f3b61..6a2a74683039923e202b4f12cfc16b84fe3fd2b4`:
45 checkpoints, comprising 19 older Portal/Gallery/Mail checkpoints, 11 early
realm packets and 15 recent Gallery/Bricks/Mail-practice packets. Transfer bundle
prerequisites preserve that history; they are not all functional prerequisites.

All 16 selected original/integrated pairs below have equal `git patch-id --stable`
values, and every integrated commit and listed merge is an ancestor of the audited
main. Full identities, patch IDs, source roots and packet prerequisites are in
[the reconciliation inventory](dependency-reconciliation-20261026.json).

| Packet | Original saved source | Integrated commit | Merged PR |
|---|---|---|---|
| Motif Studio | `dbf0f946` | `671a6df3` | [420](https://github.com/RicheyWorks/Daedalus2/pull/420) |
| Motif Study | `e2865526` | `728fee10` | 420 |
| Artist tools | `e49d1007` | `d24e0285` | 420 |
| Spectrum | `163b73e4` | `52d7fbd4` | 420 |
| Motif Rack | `197cbeaf` | `e7b89195` | 420 |
| Direct palette | `7f8fa1b2` | `f0752cff` | 420 |
| Bridge Workshop | `907c1730` | `817ed6a7` | 420 |
| Skyline Workshop | `a05fed26` | `7d9ee2d5` | [439](https://github.com/RicheyWorks/Daedalus2/pull/439) |
| Blueprint Trail | `4755bbe6` | `6500c0dc` | 439 |
| Blueprint Print Press | `553e1dc3` | `7bf3122d` | 439 |
| MailRoute prerequisite | `8afd4849` | `ec3cd77d` | [440](https://github.com/RicheyWorks/Daedalus2/pull/440) |
| Mail Practice | `1b5ec52e` | `eb59275f` | 440 |
| Bridge Walk | `5cb339ee` | `42d7e7cb` | [442](https://github.com/RicheyWorks/Daedalus2/pull/442) |
| Motif Flipbook | `76ae32ee` | `802f6653` | [444](https://github.com/RicheyWorks/Daedalus2/pull/444) |
| Kept-image Guide | `e5029420` | `969ee4dd` | 444 |
| Storyboard Press | `6a2a7468` | `2ae6e410` | 444 |

The merge commits are #420 `684460f8`, #439 `dc40225f`, #440 `91ef5fa5`,
#442 `6f522ddb` and #444 `ba55ae2b`. The old MailRoute prerequisite is the only
one of the 19-checkpoint older backlog selected by these tranches.

## Functional dependencies and coupling

- Studio → Study → artist tools → Rack → Flipbook supplies copied, immutable
  artist frames. Artist tools and Rack require the Study packet's shared
  `Private/DaedalusGalleryMotifNative.h` reader/palette API. Direct palette
  requires Studio, Study and artist tools; Rack is ancestry only. The kept-image Guide uses that
  Studio/palette state; **it has no Flipbook runtime dependency**.
- Spectrum and Bridge are independent modules. Their neighboring positions in
  the saved source history do not make them prerequisites for each other.
- Trail binds Bridge and Skyline and introduces their readiness APIs. Print Press
  needs Bridge, Skyline and that Trail/API packet, without requiring a Trail actor
  to be placed. Bridge Walk needs Bridge plus `CopyBlueprintSnapshot` introduced
  by the Print packet; it uses neither the Trail actor nor the print writer at
  runtime. Applying the unchanged Print packet also brings Skyline and Trail's
  readiness APIs. Storyboard inherits those source/API dependencies through Print.
- Storyboard needs Flipbook and the Print packet's writer extraction. Keep
  `Private/DaedalusLocalSvgFiles.h/.cpp`, `DaedalusBricksBlueprintPress.cpp` and
  `DaedalusGalleryMotifStoryboardPress.cpp` together. Omitting the helper or one
  updated caller is an incomplete integration.
- Mail Practice needs `DaedalusMailRouteCore.h` and its existing
  `DaedalusTemperForgeCore.h` RNG dependency. It does not require the canonical
  MailRoute Session/Board actors or any Gallery/Bricks packet. It remains local
  practice, with no canonical courier identity, trusted multiplayer observations,
  day retirement, settlement, reward or persistence authority.

Inventory `requires_packets` records producer-declared packet prerequisites,
including APIs introduced by another packet. It is not a claim that all current
actors must be placed, or that every historical bundle ancestor must be applied.
The existing per-packet [production handoffs](../production/) remain authoritative
for exact placement and native acceptance steps.

## Older work that must not be replayed

Subject matching alone misses adopted checkpoints. Gallery mural controls
`ca6e6e6356d1b42cd72e11ff62f0bdfc95195330` are already represented by
`b899c0004a407038dbeacbaa19a4b0ae3ec2d0fd` in [PR417](https://github.com/RicheyWorks/Daedalus2/pull/417),
merge `466b0a94dff68c0c6572f64fb17ac0fe4ff00832`: all six checkpoint file blobs
equal the audited main. Mural rebuild preservation
`8a780e530db4b824426e997cd24aa139b6141b1a` is also adopted there. Five of six
files match; `DaedalusLivingPainting.cpp` has only the later two-line
`RF_DuplicateTransient` safety addition from `d0ee0a2659542141f7e31e3f7bf04882fb14f522`.
Preserve that later fix.

The separate Gallery ArtViewer `a21c59ffb22fa3095806d3143835f408a580f5c8` is
not present: all eight added paths are absent from the audited main. Motif Study
is a different contract and does not establish equivalent viewer coverage.
The older Portal behavior/idle checkpoints and scope checkpoint remain a separate
owner reconciliation; this document does not label their behavior absent solely
because commit subjects or original SHAs are missing. They are not prerequisites
for the selected tranches above.

## Remaining early realm packets

All added paths from these eleven saved packets are absent from the audited main.
None needs the entire preceding bundle chain. “Independent” below still requires
the existing Usable/Hero/ProceduralMesh facilities and explicit safe placement.

| Packet / original saved source | Required new packets | Next gate / owner |
|---|---|---|
| Threadwalk `0e804c1828f324d441aea3817fb2a9d23171814a` | Independent | Boss selects source tranche; sole native owner accepts input/lifecycle |
| Rune Loom `e53bc6404e62cf821c65391f1f1d32c9de36c755` | Independent | Same; Threadwalk is ancestry only |
| Puzzle Lab `c794604ff7fb79db4a29689467d6ff480b23ff82` | Threadwalk + Rune cores | Optional offline consumer; prior `file:` browser route remains denied |
| Mirror Relay `309f427db5c2d8ddcdebdb5785add599952ab649` | Independent | Boss source tranche; Puzzle Lab is ancestry only |
| Stencil Studio `a25c134901b56197dfcbb1e0aaacc83e09f85c3a` | Independent | Native construction/input/lifecycle acceptance |
| Folding Hall `42f01d78308adfd5a938a96aa928d56b65dc9f38` | Independent | Native multi-occupant closure/clearance and registration; incomplete proof keeps closures open |
| Gallery Sightline `5a2825a48a1866097dd0c5f5da69d6f8b1afd671` | Independent | Actual perspective alignment; optional occlusion is not pixel-visibility proof |
| Trial Wing `f8ab2ce91b88cd1084981882f0ff6e85f59d2587` | Threadwalk + Rune Loom + Mirror Relay | Connected native tranche; Puzzle Lab is optional |
| Survey Walk `c4ca1acb5f2519f39ca259c93cd099f61362e246` | Independent | Standalone player and ground-level observations; canonical identity/progress/rewards/save deferred |
| Bricks Obby `de8c94d950d061260ef82d65e7acd17edbfe674e` | Independent | **HOLD** for native landing/rescue/health ordering |
| Kindness Garden `a8a270cf424977c11fb254d319bdf99d159e1883` | Independent | Separate small source candidate; noncolliding geometry does not establish native input/render/lifecycle acceptance |

For a future connected source intake, Boss can select **Threadwalk + Rune Loom +
Mirror Relay → Trial Wing**, adding Puzzle Lab only if wanted. Kindness Garden
is a separate small candidate. These are recommendations, not new claims,
assignments, permission to replay packets or editor-slot requests.

Obby remains held for actual jumps/grounded detection, the 125 cm assistance net,
capsule/floor refresh, occupied or changed returns, Hero landing/fall/health order,
possession, lifetime and cooking. No guaranteed health protection follows from
portable checks. No denied browser route is retried or replaced by this work.

## Checks and acceptance limits

`python -B -m unittest discover -s tools/realm -p test_dependency_reconciliation.py -v`
runs only stdlib source checks. It resolves actual project-header closures,
checks the critical cross-packet dependencies and private-writer cohort, and
exercises missing-header, private-header and include-cycle regressions. It makes
no Git/network/editor calls and does not compile C++ or execute native writers.
The recorded commit/patch identities are an audited snapshot, not re-attested by
these no-Git tests.

The existing `realms-core-tests.yml` already runs ten MSVC portable suites and
the two SVG verifiers, introduced by `850227cab2d14b78e63ca6e2a12042853d195e9c`.
This change adds the source check and relevant path triggers to that workflow;
it does not duplicate CI or rerun the existing compiler suites locally.

Merged source, portable tests, native compilation, installed plugin parity,
real input/file I/O/collision/rendering, saved/reopened behavior and cooking are
separate stages. This reconciliation establishes none of the latter stages.
Current source handoffs and the saved sole-writer checkpoint must be reconciled
by their owners before native dispatch.

Custody is separate from packet authorship. The original source handoffs name
codex-play-guard; the later 08:15 UTC coordination record names Boss, with handoff
54240 and claims 54245/54246. Reconcile the current verified handoff rather than
automatically assigning native authority to the owner named in an old packet.
