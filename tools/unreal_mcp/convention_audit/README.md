# Production-convention audit (Epic P1 candidate 3, source only)

From docs/production/epic/ueb-findings-20261019.md, candidate 3. The rules are engine-free here; the
editor side only exports one fact row per asset.

| File | Role |
|---|---|
| `audit_core.py` | Rules: `Kind_Name` names (Prop/Mob/Item/Tool/Bld/Wpn/Decal, plus M_/MI_/T_/SM_), UE-safe slot names (no `.NNN`, `#`, spaces), simple collision present (unless allow-listed), bounds 1 cm to 100 m; empty audit fails; folder digest for the before/after "nothing written" proof |
| `test_audit_core.py` | Engine-free tests |

**Not done here (editor work for the custodian, codex-play-guard):** the PythonScriptCommandlet fact
exporter, run on an isolated copy in a disposable project, inside a custody window, never alongside the
live editor and never on DaedalusRealm. Whether the commandlet needs `-unattended` is unverified; the
team launch rule bans it for editor launches.
