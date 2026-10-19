# ytm-island diag: one-off check scripts (youtube-master)

Kept so nothing lives only on BLACKBEARD. Read-only checks unless noted. Do NOT run any of these in the shared editor yourself: codex-play-guard is the sole Unreal writer; ask by NEED.

- Blender (`blender -b -P`): `check*.py` (tri/material-slot check of a polish batch from ../specs), `tricount*.py` (YTM signs/records/jukebox GLBs). They read `bot-team\art\glb` paths; edit the paths for another machine.
- Unreal read-only: `ytm_herocheck.py` (YTM_Hero actor count, PIE state), `ytm_seqcheck.py` (WB_Flythrough_* sequences exist and have keys), `ytm_find.py` (asset lookup).
- Unreal WRITES (legacy, superseded): `ytm_save.py`/`ytm_save2.py` save DaedalusWorld + the YTM sublevel, `ytm_reset.py` sets the current level, `ytm_oneshot_ue.py` uses viewport take_high_res_screenshot (writes no file in UE 5.8; use tools/capture instead).
- `ytm_wait.ps1`: waits on the team link for an editor-turn grant (reads link\log.jsonl).
