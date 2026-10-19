# disk-saver ops scripts (archived from BLACKBEARD bot-team, Oct 2026)

One-off operational scripts disk-saver ran while building DiskSaver Island, kept here so nothing lives only on
BLACKBEARD (Richey 2026-10-18 23:16). They hard-code BLACKBEARD paths (`C:\Users\730ri\projects\...`) and are a
record, not a library; the reusable pieces are the island scripts one level up and `tools/streaming/`.

- `commit*.ps1`: the copy-and-commit steps used to land island files into Daedalus2 (our files only).
- `ready*.ps1`, `ship1.ps1`: art-queue READY markers and link posts for import batches.
- `batch1.json`, `canopy_progress.json`, `canopy_todo.json`: import batch lists and the resumable canopy re-import state.
- `addcorr.py`, `fix6.py`: appended "Correction applied"/"Status" lines to BOARD/LESSONS-LEARNED-UNREAL.md.
- `diag.py`: read-only Unreal editor diagnostic (world/sublevel actor counts) for the bridge.
- `turnchk.ps1`: read-only link log check for editor turns.
- `link/disk-saver-*.ps1|py`: team-link helpers (post a note with free RAM, post with a structured `to`, poll the inbox).
