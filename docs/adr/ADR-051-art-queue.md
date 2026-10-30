# ADR-051: The art queue, Blender team to Unreal with no one relaying

Status: accepted, 2026-10-12

## Why

Richmond: the Blender team (other bots) builds assets that have to feed Claude in Unreal, "a lot of stuff, in
real time", and it goes on the lead bot's plan of the day. Relaying every hand-off by chat doesn't scale.

## Decision

One shared folder on Richmond's PC, `projects\bot-team\art\`, and a watcher that never sleeps:

- `BRIEF.md` (from `docs/BLENDER-TEAM-BRIEF.md`) holds the rules the judge checks: metres, applied scale, origin at
  the bottom, triangle budgets by kind, ≤ 3 material slots, `Kind_Name` names. It also holds the asset list.
- **`QUEUE.md`** is the board. Its status flow is TODO → DOING (who) → READY → SHIPPING → SHIPPED (tris, size) or
  REJECTED: <check>.
- **`asset_pipeline.artqueue`** (`art-queue.ps1 -Start/-Status/-Stop`) reads the board every 10 s. For each READY
  row:
  - It waits for both bridges and for Unreal to be out of Play.
  - It opens `<Kind>\<Asset>.blend` in Blender, but never over unsaved work in another file (that row shows
    `WAITING`).
  - It exports the asset's collection, ships it through the pipeline's judge into `/Game/Daedalus/Art/<Kind>`, and
    adds the brief's budget and slot rules.
  - It writes the result into the row, `reports\<Asset>.json`, `feed.jsonl` (for the lead bot) and `STATUS.md`.
- **Board edits are compare-and-swap.** Only the row's Status and Notes cells change, and only if the file didn't
  change since it was read, so a bot claiming another row at the same moment keeps its claim.

## Proven

- `harness/artqueue_test.py` **29/29** against fake bridges and a stub `bpy`. It covers:
  - bridges down, Unreal in Play, the happy path, never shipping twice, and unsaved work kept;
  - over budget, too many slots, a judge failure, a bad name, no meshes, and a bridge error (row back to READY);
  - a concurrent claim surviving, and the real Blender-side open script.
- Mutants: 7 of 7 killed.
- The pipeline's `run_all` is 4/4: glb 10, judge 17, artqueue 29, e2e 18.
- **Live on Richmond's PC:** a two-part crate built in Blender, saved to `art\Prop\` and marked READY shipped on
  its own about 10 s later: `SHIPPED (24 tris, 1.05 m)` in `/Game/Daedalus/Art/Prop/Prop_PipelineCheck2`.

## What the live runs found

1. **The watcher's own reject worked first.** Before the crate existed it answered "no meshes (make a collection
   named …)".
2. **Unreal can't load or save imports during Play.** The judge saw 0 meshes. The watcher now waits for Play to
   end.
3. **UE 5.8.3 reports only meshes as imported.** The import now counts the materials the meshes reference.
   A folder listing was tried first; the e2e canary rejected it because it counted leftovers.
4. **The import made during Play poisoned its folder** until an editor restart (grid material fallback). Shipped
   under a fresh name.

## Held

- Asset placement in the game: swapping the foes' cones for `Mob_*` meshes and the pick for `Tool_Pickaxe`.
- A NOTES auto-answer.
- The lead bot's daily digest from `feed.jsonl`.

## Amendment, 2026-10-12: BLOCKED is not REJECTED

The Blender team (blender-harness) found that a READY row was marked REJECTED because Unreal failed on its own
side: an import ran while a game test was going and made nothing. REJECTED tells a team to fix the asset, so that
was the wrong word. The watcher now writes `BLOCKED: <why>` when the failure is Unreal's:
- the bridge raised an error;
- or every Blender→file check passed and Unreal reported an import error or made no mesh.

BLOCKED rows are retried by themselves every 60 s (`BLOCKED_RETRY_S`), and STATUS.md lists them as "blocked on
Unreal". A failure on Blender's side stays REJECTED.

The tests went from 31/31 to 38/38. A mutant that drops the classification fails 3 of them.
