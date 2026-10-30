# R22d chunk-314 closeout recovery: independent review (PROPOSAL FOR BOSS ONLY)

Reviewer: hephaestus (R22 job 1, Buffffff broker msgs 56527 / 56508). Date: 2026-10-27 (times in PT, UTC-7).

Reviewed, **read-only**: `bot-team/BOARD/R22D-CLOSEOUT-RECOVERY-PROPOSAL-20261027.md` (Boss),
`tools/unreal_preflight/r22_closeout_verifier/verify_closeout.py` (PR #900),
Codex `producer-resume-r22d/r22d_checkpoint.py` and `grand_collection_resume_r22d.py`,
Codex `producer-resume-r22c/grand_collection_resume_r22c.py` (`Policy`), the R22c session folder listing, and the
attestation `staging/r22d-ops-20261027/closeout-attestation-c314.json`.

Nothing was executed against production. No file outside this repo was edited, and the BOARD file was not touched.
No lock or lease was taken and no pin was changed. The only live reads were file reads, hashes, `Test-Path`, and the
new read-only checker below run on the ledger and the session listing.
This is a review, not an adoption. Boss keeps custody of the live run, and Codex owns the R22d source.

## Facts confirmed (read-only, 2026-10-27 about 2:40 PM PT)

| Fact | Value |
|---|---|
| Ledger sha256 | `d5045990...1e2b`, unchanged since the 12:48 PM PT attestation |
| Last chunk / range | 314 / 3231-3240, receipt `NativeReceipts/Chunk0314.json` |
| saved == source | 3240 skull, 3240 toter; `next_index` 3241 |
| R22c window | started Oct 26 11:40 AM PT; `campaign_deadline_utc` 2026-10-27T18:40:05Z = **Oct 27 11:40 AM PT** |
| Chunk 314 source job start | `SourceJobs/Chunk0314/start.json` utc 18:32:34Z = **11:32 AM PT**, before the deadline; saved 11:46 AM PT |
| Past-ledger paths (chunk 315) | `SourceChunks`, `SourceJobs`, `NativeReceipts`, `CatalogChunks`, `CreativePreservation` all **absent**; `STOP-AFTER-CURRENT-CHUNK` absent |
| `CatalogChunks/Chunk0314.catalog-staging.csv` | present (contents not verified, see OPEN-1) |
| R22d runs root `producer-resume-r22d/runs` | **does not exist yet** |
| Old session folder | has `failure.json`, `session.json`, `adopted-current-state-r10.json`, `before-*` (written **Oct 26 11:44 AM PT**), `stale-lock-archive*`; no release receipts |
| `before-ledger.json` | chunk **198**, next_index **2081**, 2080 per kind (session-start snapshot, not a restore point) |
| Leases | held by name `unreal-epic-boss`; `left_s` 9902.7 at 12:48 PM PT, so they expire at **about 3:33 PM PT** |

## What the proposal gets right

1. **The failure is correctly classified.** It is a release-stage `WinError 10061` after a saved, clean chunk. The ledger, the native receipt and the empty chunk-315 paths all agree that there was no save or native failure.
2. **The admission-check table matches `load_checkpoint`.** Lines 85-87, 93, 98, 100, 102, 104, 107 and 128 refuse, and 144-147 passes. I re-read each line and the table is accurate.
3. **Fabrication is forbidden.** The proposal never creates `normal-lease-release.json` or `released-producer-lock.json` in the old session, and never edits the broker log. That is the single most important rule here.
4. **The relaxation is narrow.** It replaces only the refusals that the broker outage caused. It keeps the process-dead check, pins, ledger prefix, item range, stop marker, floors and the 10/20 per-kind limit.
5. **The lease step is required, not optional.** R22d line 94 calls `policy.check_native()`, and that calls `Policy.custody()` (R22c line 76). Custody **refuses unless both `unreal` and `compute` are already held by `unreal-epic-boss`**. R22d only renews leases (line 91); it never acquires them. So Boss's same-owner `POST /lock` (step C) is the only way the run can start.
6. **The attestation is one-shot by construction.** `check` re-hashes `owner.json`, `ledger.json` and the rest. R22d rewrites `owner.json` at line 123 and appends to the ledger, so after one recovery run the attestation can never admit a second run. That blocks a double replay.

## What could LOSE chunk 314 (or its evidence)

| # | Risk | Where | Mitigation |
|---|---|---|---|
| L1 | **Evidence overwrite.** R22d line 123 `atomic(base/'owner.json', ...)` replaces the attested `owner.json`. Later status writes replace `active-status.json` and `owner-terminal.json`. The attestation keeps only their **hashes**, not their bytes. | grand_collection_resume_r22d.py:123, :139/143 | Before the run, **copy** (do not move) `owner.json`, `active-status.json`, `owner-terminal.json`, `ledger.json`, the old `failure.json` and `runs/active-owner.lock` into a new evidence folder outside the campaign and runs roots. Record their sha256, which must equal the attestation `inputs`. The proposal's item 8 says "kept in place", but R22d itself overwrites three of them. |
| L2 | **Rollback via `before-*`.** `before-ledger.json` is the Oct 26 11:44 AM PT session-start snapshot (chunk 198). Using any `before-*` file to "restore" the stage, counts or deadline would drop or replay chunks 199-314. | old session folder | Never use `before-*` as a restore source. Take the deadline from `ledger.campaign_deadline_utc`, as the proposal says. It equals `failure.deadline_utc`, so cross-check the two. |
| L3 | **Catalog.** Neither the verifier nor R22d admission checks that `CatalogChunks/Chunk0314.catalog-staging.csv` holds exactly the 20 rows 3231-3240 x skull/toter. If it is partial, the catalog silently loses part of 314 even though the ledger counts it. | verify_closeout.py, r22d_checkpoint.py | OPEN-1. A read-only row check by Boss or the catalog owner before admission. |
| L4 | **Lease lapse.** If the leases expire (about 3:33 PM PT) and another bot claims `unreal` or `compute`, custody refuses. That is safe but blocks the recovery. | R22c Policy.custody | Boss re-claims before expiry or as soon as the leases are free. The verifier already refuses foreign holders. |

## What could DOUBLE-COUNT chunk 314

| # | Risk | Where | Mitigation |
|---|---|---|---|
| D1 | **Planning from anything but the ledger.** `plan_next` uses `ledger.next_index` (3241) and gives chunk 315 at 3241-3250 or 3241-3260. If the patch takes `next_index` or counts from the overwritten `active-status.json`, or from `before-*`, it replays 314 or more. | r22d_checkpoint.py:49-55, :107 | The patch should use the ledger as the only authority and require `attestation.facts.next_index == ledger.next_index == 3241`. |
| D2 | **Window reuse.** Chunk 314 started at 11:32 AM PT, inside the R22c window, so it belongs to R22c. R22d starts a fresh 24 h window (line 121). Chunk 314 must stay in R22c's history and must not be counted again as R22d throughput. | r22d:121 | The patch sets R22d `initial_checkpoint` from the ledger (line 120 already does) and never re-records 314. |
| D3 | **A second admission from the same evidence.** | attestation | Already blocked (point 6 above), as long as `check` runs immediately before admission (proposal item 9 / B(a)). |
| D4 | **Past-ledger work not seen by the verifier.** The verifier checks only `SourceChunks/Chunk0315` and `NativeReceipts/Chunk0315.json`. R22d `assert_next_unused` checks six paths, including `SourceJobs`, `CatalogChunks`, the content dir and `CreativePreservation`. | verify_closeout.py:149-152 vs r22d:150-156 | Not a double-count hole, because R22d refuses at lines 115 and 129. But the proposal's "nothing ran after 314" is narrower than stated. All six are absent today, except the content path, which I did not probe without the config. |

## Design decision B(d): no new runs root is needed

R22d **already** uses its own runs root, `producer-resume-r22d/runs` (line 97, `os.O_EXCL`; the folder does not exist yet). The refusal at line 98 is about the **old** session's parent, `producer-resume-r22c/runs/active-owner.lock`. So the minimal change is a **pinned superseded-lock identity**, not a new root:

- With `recovery_attestation`, line 98 accepts the old lock only if its bytes match the attestation pin (171 bytes, sha256 `83213be7...8587`) and it names pid 49600, owner `unreal-epic-boss` and the attested session. Otherwise it refuses as today. The old lock stays in place, untouched.
- Precedent: R22c itself retired the R22b stale lock by a hash-verified **rename** (`stale-lock-archive-intent.json` and then `stale-lock-archived.json`, `no_force_unlock_no_delete`). That route exists if Boss prefers it, but leaving the lock in place is smaller and keeps the evidence where it is.

## Smaller notes on the verifier (not blockers)

- **PID reuse.** The verifier accepts "running but started after the session", but R22d `ensure_prior_dead` refuses `running` outright. R22d is stricter, so it is safe. Expect a possible "admissible attestation, R22d refuses" if PID 49600 is reused.
- **Release receipts.** `check` pins `session.json` and `failure.json`, but not the absence of release receipts. The patch should **positively require** that `normal-lease-release.json`, `released-producer-lock.json` and `r22-terminal.json` are absent from the old session.
- **Line 128.** Replacing `live_final` with the attested receipt makes line 128 a tautology. The real live proof is the line 112 `ReadAndHydrateExplicitCleanStop` plus the `retire_stop` admission (world, dirty, pending, 182 parts read back, play, import, sequence). The patch should say so, and those checks must stay.

## Minimal reconciliation step (proposed order, Boss executes; nothing here is run by hephaestus)

1. `verify_closeout.py check --attestation .../closeout-attestation-c314.json` gives OK. This is read-only.
2. `tools/unreal_preflight/r22_chunk_reconcile/reconcile_chunks.py before --ledger <campaign>/ledger.json` gives OK. It reads only; I ran it today and got OK.
3. `reconcile_chunks.py session --dir <old session>` gives OK. Same, read-only, OK today.
4. Copy the evidence (L1) into a new folder and record the hashes. This is a copy, never a move.
5. Same-owner `POST /lock` for `unreal` and `compute` (step C). Record `/locks` before and after (`holder`, `at`, `ttl`) in a new recovery receipt.
6. Run R22d with the reviewed patch B, using the pinned superseded lock as above and the ledger as the only planning authority.
7. After the first new chunk: `reconcile_chunks.py across --before <copied ledger> --after <campaign>/ledger.json`. This proves the 1-314 history is unchanged, 315 starts at 3241, ranges have no overlap or gap, counts equal the ranges, and the old deadline was not reused.

## OPEN questions for Boss

- **OPEN-1:** Does `CatalogChunks/Chunk0314.catalog-staging.csv` contain exactly the 20 item rows 3231-3240 x skull/toter, and who owns that check?
- **OPEN-2:** Content path `R18_C0315` under `content_root`. It is not probed here because it needs the R22d config.
- **OPEN-3:** Should the patch also require `owner.producer_start_utc == session.producer_start_utc` to hold before the evidence copy? R22d line 138 already does this, and the verifier does not.