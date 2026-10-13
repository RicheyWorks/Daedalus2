# Dungeon Master → Labyrinth: first native integration

Owner: team-codex, 2026-10-13. Native actor/UI attachment and live acceptance: unreal-team (Claude). This optional consumer embeds the existing Java game into Daedalus's existing Labyrinth realm. It does not replace the maze or reimplement combat in C++.

## Source and boundary

Source: `RicheyWorks/ai-dungeon-master`, upstream commit `9dadff2f69eb4e8d504f0044130b5fada6f74f43`. The local dirty checkout at `3a1ccd2` was inspected but not changed. The newer source contains authenticated per-session `GameInstanceService` isolation. Relevant sources are `service/src/main/java/com/xai/dungeonmaster/dto/GameStatusV2.java`, `service/.../config/RequestIdFilter.java` and `service/.../service/GameInstanceService.java`.

Java remains authoritative for party, combat, choices, quests and history. Native Unreal renders the state, accepts a currently offered choice and displays the returned state. Optional narration is presentation only. No client-side rewards, inventory transfer, save/load/reset calls or engine migration are included.

| Request | Contract |
|---|---|
| GET `/v2/status` | Envelope `type=game_status`, `version=1`, `payload`, correlated `requestId` |
| POST `/v2/action` | JSON `choiceLabel` copied from the last accepted choices; same status envelope returned |
| Headers | Existing session bearer and fresh `X-Request-Id` per request |

The response subset consumed is party name/role/HP/maxHP/alive, chaos, combat, available choices, recent history, location, play hint and optional quest title/progress/scene/completion flags. Quest progress is **0–1**, not 0–100. Extra fields are ignored. The native acceptance limits are deliberately conservative (16 party members, 64 choices, 30 history lines, 64 KiB response, depth 32); oversized valid server content is refused rather than partially displayed. The 64 KiB check is an acceptance bound after HTTP reception, not a transport allocation cap.

## Host integration

Create and destroy `MakeShared<FDaedalusDungeonClient>()` on the game thread. Configure a deployment-owned HTTPS URL (loopback HTTP also accepted) and an already established session bearer. The host must enforce `game.auth.enabled=true` on the Dungeon Master service; attaching a bearer alone does not prove authentication is enforced. Never obtain this URL or credentials from generated story text. Never log or replicate the bearer.

Call `Refresh()` at entry, render `State().State()` and `Error()`, and enable actions only when `State().Ready()`. Call `Choose(Index)` once for a deliberate click on a displayed choice. One request at a time; HTTP completion explicitly runs on the game thread. On realm exit, `Cancel()` unbinds transport callbacks. A weak owner and monotonic request ID prevent stale completions from changing another session.

**Uncertain actions are not retried.** The upstream request ID is correlation, not an idempotency key. Timeout, cancellation, malformed response or other action failure blocks further choices. A subsequent status read can refresh the display but does not prove whether the prior action committed, so it cannot unlock mutation. Recovery requires host reconciliation or a genuinely new authenticated backend session. Changing configuration must not be used to bypass this rule. Token renewal for an existing session is not a new game session.

No changes to the module's dependency list are necessary: HTTP and Json are already private dependencies. The public client header forward-declares its transport type.

## Blender kit

Run `blender --background --python tools/blender/dungeon_master_kit.py -- OUTPUT` to reproduce eight original static interaction props. Each GLB exports at its own base origin in metres, with a role and hash in `manifest.json`; the saved scene arranges them only for the contact sheet.

| Prop | Intended visible binding |
|---|---|
| NarratorLectern | Authoritative scene text and available choices |
| ChoiceTrident | Current choice selection |
| ChronicleArchive | Recent history, with no action replay |
| QuestSeal | Quest status and progress |
| ReturnWaymarker | Local navigation; not an alternative realm portal |
| RiftThreshold | Dungeon-room threshold; no automatic realm transfer |
| PartyRally | Party health/combat display |
| RewardReliquary | Reward presentation only; grants remain server-owned |

Reuse existing `Prop_Chest`, `Prop_Realm_Stairs`, `Prop_Sign`, `Prop_Torch_Wall` and `Prop_Workbench` for ordinary dungeon furniture. This kit fills interaction silhouettes rather than duplicating those assets. It is not a rigged character roster and contains no animations, authored collision, Unreal placement or live interactions. LOD reductions are not claimed for these small meshes.

Local artifacts: `C:/Users/730ri/Documents/Codex/2026-10-13/dungeon-master/art/`. Contact sheet and `.blend` included. Eight meshes total 836 triangles before import.

## Evidence and Claude acceptance

- Portable policy: 47 passing MSVC C++17 checks under `/W4 /WX`, including malformed state, stale completion, unavailable choice, string escaping and uncertain-action recovery restrictions.
- Actual UE 5.8 client translation unit compiles using the installed compiler and UBT-generated module flags from Poot's isolated host; response file adapted into our own output directory. Poot's files remain unchanged. This is compile proof, **not a full link, editor load or live service test**.
- Blender 4.3 generated eight GLBs, manifest, saved scene and rendered labeled contact sheet; visual inspection completed.

Claude's next acceptance: link/load in the realm host; configure the isolated authenticated service; show a real status at the lectern; choose one real option and show the changed room/UI state; prove session separation; leave during a pending request; simulate timeout and malformed response and show retained display plus disabled actions. Record screenshot/video and exact source heads in the registry. Until then the slice is **code/art ready, live integration pending**.

## Lessons carried forward

Check upstream against dirty local copies before selecting an API version. Reuse generated engine compile settings without borrowing another bot's writable outputs. A correlation ID is not replay protection. Keep art readiness distinct from a working in-game interaction. Announce exact claims early: Poot's game inventory included Dungeon Master, and the team was notified that this bridge already owns that scope.

### Repeatable policy regression runner

Run `python engines/unreal/core-test/run_dungeon_checks.py --compiler cl` in an MSVC developer shell, or select `g++` / `clang++` with `--sanitize` on Linux. The runner builds in a temporary directory and verifies both the 47-check baseline and three deliberately broken policies: accepting stale responses, replaying uncertain actions, and incorrectly unlocking actions after a status refresh. It requires each mutant to fail the intended assertion, not merely crash. The dedicated Native Dungeon policy workflow covers stacked PRs as well as main. Local Windows baseline and all three mutation detections passed; Linux sanitizer results are reported by CI separately.
