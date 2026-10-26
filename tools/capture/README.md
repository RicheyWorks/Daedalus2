# tools/capture: in-game proof capture kit (capture/v1)

Owner: youtube-master. Registry row: "In-game proof capture kit" in `bot-team/BOARD/ARCHITECTURE.md`.

The registry says a component only reaches **IN-GAME-DEMO** with an in-game screenshot or video. This kit
turns that into one bridge call per editor turn, for any island or system.

* `capture_job.py`: the `capture/v1` job schema (engine-free): validation, camera maths, `manifest.json`.
* `capture_ue.py`: Unreal runner. Stills come from one temporary SceneCapture2D, a render target and a PNG export.
  This is disk-saver's proven path. Viewport high-res screenshots wrote no file in round 5.
  The runner sets a fixed exposure on the capture component and adds no lights. It removes its temp actor and saves nothing.
  Optional short MRQ clip (`CAPTURE_CLIP=1`), skipped below `clip.min_free_gb` of free RAM.
* `jobs/*.json`: one job per island or system. `jobs/ytm_island.json` is the Youtube Master Island example.
* `test_capture.py`: offline tests, including the runner against a mocked `unreal` module.

## Use it in your turn
```python
CAPTURE_JOB = r"C:\Users\730ri\projects\Daedalus2\tools\capture\jobs\ytm_island.json"
exec(open(r"C:\Users\730ri\projects\Daedalus2\tools\capture\capture_ue.py").read())
```
Output: `<out_dir>/<job>/<job>_<view>.png`, a basecolor still for checking dark versus missing geometry, and
`manifest.json` (`capture/v1/manifest`: component, commit, time PT, files, complete, errors). Link that manifest in the
registry row when you move it to IN-GAME-DEMO. Save your own sublevel afterwards, following the turn rules.

## Job format
```json
{"schema": "capture/v1", "component": "<registry component>", "name": "snake_case", "sublevel": "<streaming level>",
 "origin": [x, y, z], "views": [{"name": "overview", "eye": [dx, dy, dz], "target": [dx, dy, dz]}],
 "width": 1600, "height": 900, "fov": 70, "ev100": 9, "basecolor": true,
 "clip": {"sequence": "/Game/...", "start": 0, "frames": 180, "fps": 30, "min_free_gb": 2.0}}
```
Eye and target values are cm offsets from `origin`. Keep clips short (at most 900 frames; 180 fits a 10-minute turn).

## Daedalus tie-in
Every island is a fragment of the one shattered planet. A capture job is that fragment's survey record, its proof that it
still holds life. The recording-isle video pipeline (box-side ffmpeg) turns these stills and clips into the channel cut.

Tests: `python -m unittest tools/capture/test_capture.py` (or `python test_capture.py` in this folder).
