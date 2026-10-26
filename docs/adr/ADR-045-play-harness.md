# ADR-045: The play-test harness and one-call builds

Status: accepted, 2026-10-12

## Why

Richmond: "work on your harness capability, that needs to be a more robust interface between you and Unreal".
What slowed this week down:

- Each check of a mechanic was hand-written Python, and one `execute_python` call is one frame.
- A build cost a dozen polling calls.
- A background editor runs Play at about 3 fps.

## Decision

- **`daedalus_play.py`** (DaedalusLink `Content/Python`, registered as bridge commands):
  - `daedalus.play_scenario {name}` starts a scenario that runs frame by frame inside Play (a slate post-tick
    generator). `daedalus.play_status` returns its checks (PASS/FAIL with details) and record.
  - Scenarios: `shoot`, `views_layouts`, `ghost`, `foes_hunt`, `shield`. A new one is a generator that yields per
    frame and returns checks.
  - `daedalus.play_snapshot` returns, at any time: hero vitals, each foe's state, routes and attacks, the Ghosts,
    the nav stats and fps.
  - `daedalus.full_speed` turns off the background throttle through the console and the editor ini. The setting
    isn't exposed to Python, so it holds from the next editor start.
- **Hero hooks** where Python can't reach (world subsystems): `NavStats`, `NavProbe`, `NavTrace`.
- **`engines/unreal/unreal-job.ps1`**:
  - `-Start` pulls, builds and reopens the editor in a job that outlives the calling shell.
  - `-Wait` blocks up to 50 s and answers RUNNING, BUILD OK (with the bridge state) or BUILD FAILED with the
    compiler errors.
  - The job runs from the repo in a visible minimized window, not from %TEMP% hidden.
- **Dialog watcher** also notes security-software windows in its log and leaves them for the person.

## Results

The whole suite passes, 22/22 checks on UE 5.8.3:

| Scenario | Checks |
|---|---|
| shoot | 5/5 (4 kills, 60 EXP = ADR-037) |
| views_layouts | 3/3 |
| ghost | 4/4 (3 kills in 27 shots, credited to the rider) |
| foes_hunt | 6/6 |
| shield | 4/4 |

Run history:

- foes_hunt 6/6 and shield 4/4 on the first runs. Their findings are in ADR-044.
- The ghost scenario's first run failed (3/4). The scenario was at fault: it spawned foes from a mounted hero, on
  another tier. The snapshot from that run also exposed the A*-every-frame cost.
- A build now takes 2 to 4 calls instead of 10 to 12.
