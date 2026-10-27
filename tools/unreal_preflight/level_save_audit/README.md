# level_save_audit

Read-only scan of editor Python scripts for saves that can write the persistent `DaedalusWorld` map
(the risk behind "no saving any level outside the producer"). It edits nothing.

```
python tools/unreal_preflight/level_save_audit/level_save_audit.py --root . --json level-save-audit.json --md level-save-audit.md
```

Grades per call (file grade = worst call):
- **HIGH**: blanket `save_all_dirty_levels` / `save_dirty_packages*` with no world guard; `save_current_level` with no
  map load and no guard; any save after loading DaedalusWorld itself; an explicit save naming DaedalusWorld.
- **MEDIUM**: `save_current_level` after the script loads/creates its own map, with no guard.
- **LOW**: a guard refuses when the open world is DaedalusWorld (a line naming it with a world/path read and a
  raise/return/exit within 3 lines), or explicit package/map saves of other maps.

Calls inside string literals (code sent to the bridge) are included and marked. Test files, `tests/` and `fixtures/` folders and `tools/unreal_preflight/` (the lint tools that name these calls) are skipped. The grading is a static heuristic: a HIGH row is a call to review, not a proven bad save.
Exit 0 when nothing is HIGH, 1 otherwise. Owners decide fixes; this report only lists them.
