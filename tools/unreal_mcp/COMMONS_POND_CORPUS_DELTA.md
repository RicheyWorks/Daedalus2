# OperatorR1 corpus blocker — v2 source inventory handoff

The old 512-mesh cap was a fixture-size assumption. Actual saved checkpoint
`C:/Users/730ri/Documents/Codex/2026-10-14/task-2/native-ingestion/CommonsPond20261023/OperatorR1/blocked-closeout.json`
and adjacent reconciled evidence report **prepared 3, imported 0, admitted 0,
held 3; no queue created; compute released**. Source-image review is complete;
do not repeat it or ask the user for authorization again while its pins match.

Actual registry path evidence has 2,119 distinct StaticMeshes: CodexContest 1,319,
ClaudeIslands 782, NativePool 18. There are 339 direct folders; largest direct
mesh folder has 376. The retained path capture SHA256 is
`125864e7af714cb576fd7d76b0b69adbdfde525a0ce4ba712856efdfa59f3287`;
its sorted object-path digest is
`be785a5a724cb442dd3ce3ff23eabd41bfc2e1d3037c246607e6a2202523b7c1`.
It explicitly says `source_hashes_verified=false`: paths are not source hashes.
The file-only reader accepts all 2,119 actual paths, including the existing
`Bld_Sunspool_BronzeSunRim-0_4` name. New destination naming rules stay unchanged.

## What changed

- No larger monolithic mesh cap or truncated prefix. Registry traversal visits
  the root and every cached descendant directory, querying each nonrecursively,
  with cooperative yields, memory/time/STOP checks and duplicate/outside-row
  refusal. The complete current count/digest is checked before and after source
  evidence verification. The global-name check uses the same directory traversal.
- Installed `IAssetRegistry.h:310-312,677-679` exposes `GetAssetsByPath` and
  `GetSubPaths` to Python as array APIs. There is no offset/limit API here.
  Directory arrays are honestly materialized; source metadata is separately
  paged. The positional `get_sub_paths(root, True)` avoids guessing a keyword.
- One guarded read request captures at most 32 mesh metadata rows, for at most
  30 seconds between safe boundaries. Each row records the actual native source
  SHA256 and saved package SHA256/bytes/path. No import/save, forced GC/unload,
  settings edit or original package mutation is added. Partial/unknown results
  remain evidence and cannot be sealed as a complete inventory.
- A small pinned v2 index binds every ordered page, the same editor generation,
  native-reader bytes, registry capture and exact coverage. Duplicate JSON keys,
  page files/paths, offsets, gaps, overlaps, conflicting DONE outputs and changed
  files refuse. Existing multipart meshes may share a source hash; a match to
  the candidate hash still blocks another import.
- During admission/import, source evidence and saved package hashes are streamed
  page by page. The 2,119 original meshes are not all loaded again. The existing
  clean-state guard and exact before/after corpus coverage bind that saved native
  evidence to current state. Only complete coverage produces `dedup-coverage.json`.
- The host request now passes the pinned baseline filename rather than embedding
  its 646,900-byte JSON. Offline preparation validates the complete page structure
  before output creation; malformed dedup data no longer passes preparation.

## Exact next operations for the sole writer

Apply only the new delta commit on PR415 to the writer checkout at its next safe
boundary. Keep all OperatorR1 files. That refusal is known terminal, not an
uncertain import, and there is no old queue to reset. New native wrapper/policy
bytes use adapter ABI `daedalus.qualified-static-owner-adapter.v2` and a NEW state.
The retained source qualification can be reused unchanged if all source/view
pins still match. Capture a new baseline only if current files/context differ.

1. Retain the existing exact 2,119-path `registry-corpus-paths.json`, or obtain a
   fresh complete path capture through `capture_registry_steps(config)` using the
   same existing guarded `daedalus.steps` route. A path capture alone is not source
   verification. Its current contents will be re-enumerated before any import.
2. Use the existing owner guard, custody/resource floors and exact protected-file
   preservation for **each read request**. Execute the pinned updated native `.inc`
   into a private scope, then return `capture_inventory_page(config)` as that
   guard's action. The helper itself checks editor/context/idle state; it relies
   on the outer established guard to hash/preserve baseline files. Do not call
   it through an unguarded alternate transport.

   `config` contains `editor` (baseline editor object), `engine_version` (actual
   native version), `baseline` (current baseline file witness), `registry`
   (complete path-capture witness), `reader` (updated `.inc` witness),
   `inventory_reader` (`static_source_inventory.py` witness), aligned `offset`,
   and optional owned `stop_path`. All witnesses are exact absolute
   path/SHA256/bytes. The native module performs no top-level effect beyond imports
   and function definitions; invoking this page function is read-only.

   Start at offsets `0,32,...,2112`. Store each actual returned page as a new owned
   file (the last requests 7 rows). Do not modify its fields or keep a cap-sized
   subset. Collecting all current pages takes 67 bounded calls, which the writer
   can loop through its existing guard without model calls per page. After a
   known terminal read failure, an incomplete page can be read again into a NEW
   file; preserve the failed evidence. An uncertain native request must first be
   reconciled normally. No retry here authorizes an import replay.

   `state=partial` means a time/STOP boundary; `state=unsupported` includes missing
   native source hashes. Keep exact issues. Unknown provenance is a real hold,
   not a reason to infer hashes from filenames, skip NativePool or fabricate data.
3. Write an explicit JSON array of the 67 selected complete page filenames, in
   offset order. Seal it entirely offline:

```powershell
python tools/unreal_mcp/build_static_inventory.py --registry C:/owned/registry-corpus-paths.json --baseline C:/owned/current-baseline.json --page-list C:/owned/complete-pages.json --output C:/owned/source-inventory-v2.json
```

4. Supply that new index as `--dedup` to the existing
   `prepare_static_profile.py` command. It pins the index and the reader (one
   dependency); page files are transitively hash-bound, preserving the 32-dependency
   ceiling. Preparation creates a NEW state without any host/editor import.
5. Use the existing runner `run --max-items 1` only in the writer's authorized
   editor window. Check complete coverage, exact source/destination, native save,
   native Valid and protected state, then saved resume without another effect.
   No live import, validation or new native page execution has been done by the
   offline code worker; adoption remains untested until this owner step.

## Explicit resource and unsupported boundaries

This supports the observed corpus; it does not promise arbitrary registry size.
Limits apply to resource units: 32 rows/128 KiB per source page; 16 MiB path text;
16,384 returned directories; 4,096 asset rows in any one direct-folder array;
100,000 total registry asset rows. A larger single-folder array cannot be paged
by the installed API and is explicitly unsupported, never silently sliced.
Each registry traversal checks a 30-second boundary; package verification checks
a 60-second boundary and yields per page. The existing native call remains 240
seconds; importer deadline/reserve are unchanged. Exceeding a time/memory/STOP
boundary means incomplete coverage and no new import, not relaxed acceptance.

Physical/commit floors remain 1,740,800,000 / 2,252,800,000 bytes; metadata work
requires an additional 128 MiB reserve. Page loads may increase Unreal's cached
memory; low memory holds instead of forcing GC or unloading someone else's work.
Index JSON remains at most 2 MiB; complete path captures allow 16 MiB plus small
headers. Package witnesses retain the existing 256 MiB individual-file bound.
The existing context cap is 4,096 actors (actual 713), independent of mesh count.
The pinned importer's own global-name preflight is unchanged and runs only after
the bounded wrapper has established complete registry counts.

Remaining genuine unsupported case: source metadata absent on any of the 2,119
meshes. No source hash reads occurred in OperatorR1, so availability is not yet
known. Missing `codex_sha256`, changed packages, incomplete pages or a different
editor/corpus must remain held. NotValidated/Skipped/native acceptance is unchanged.

Offline validation: **92 focused tests passed in 26.347 seconds**: 22 strict
inventory tests, 17 AST-isolated native registry/page tests, 25 profile/preparation
checks and 28 unchanged queue/Coupler checks. This includes 2,501 rows with no
512-row prefix, a short final page, partial pages/indexes, duplicates, corpus and
editor mismatch, real captured 2,119 paths, changed package files, candidate-hash
collisions, zero mesh loads during deduplication, bounded 32-load capture pages,
memory/STOP/deadline holds and original interruption/no-second-effect behavior.
Tests use synthetic plain-text packages/fake Unreal objects or captured JSON;
the updated native helpers have never been invoked in Unreal by this worker.
The unchanged atomic receipt writer required the normal reviewed Windows test
environment; no weaker writer/security setting was introduced. Free physical
memory after checks was 10,338,504,704 bytes, above the required floor.

**Lesson for later shared-file append:** A fixture corpus limit is not a production
resource bound. Inspect the actual corpus before publishing a reusable profile;
bound directory responses, source pages, bytes, time and memory separately while
proving complete coverage. Keep path enumeration distinct from source-hash
verification. Page receipts need exact count/order/digest/provenance and saved
package binding; truncation, missing pages or unknown hashes never prove absence.
