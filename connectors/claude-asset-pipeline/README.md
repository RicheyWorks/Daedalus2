# Claude Asset Pipeline

Moves models from Blender into Unreal and proves nothing was lost on the way. Any agent can run it: Claude, Grok
bots, scripts or CI. It uses only the Python standard library.

![Blender scene: a two-material lamp, a bevelled crate, a bare stone](docs/images/blender-scene.png)

```
python -m asset_pipeline --name Lamp --objects Lamp,Post --dest /Game/Daedalus/Props --report lamp.json
```

1. **Blender** (the [Claude Blender Connector](https://github.com/RicheyWorks/claude-blender-connector),
   port 9876) exports the objects to one `.glb`, with modifiers applied. It reports the triangles,
   materials and size of each object.
2. **The file** is read here, with no 3D library. It is the witness between the two editors.
3. **Unreal** (the [Claude Unreal Connector](https://github.com/RicheyWorks/claude-unreal-connector),
   port 9877) imports the `.glb` with an automated Interchange import, so no dialog opens. It reports the
   static meshes and materials it made.
4. **The judge** compares Blender with the file, and the file with Unreal: object and mesh counts,
   triangles, material slots, and sizes (metres to centimetres, sorted so the Y-up/Z-up swap doesn't
   matter). It prints `SHIPPED` and exits 0, or `REJECTED` and exits 1.

![Shipped: every check green](docs/images/shipped.png)

One triangle lost on import, and the judge names the check:

![Rejected: triangles: file = Unreal](docs/images/rejected.png)

Both editors must be open, with their connectors running, on the same computer.

From code: `from asset_pipeline import ship; report = ship.ship("Lamp", ["Lamp"])`.

## Import a saved Blender handoff

For a spec-1 `art/jobs/<Asset>.json` handoff, use the saved GLB without reopening Blender:

```
python -m asset_pipeline.ship_saved --job C:/Users/730ri/projects/bot-team/art/jobs/Prop_Shroom_Embercap.json --report embercap.json
```

The manifest must identify `art/glb/<Asset>.glb`, its SHA1, a passing selfcheck, and matching mesh facts.
The importer checks the saved bytes, budgets and material slots before contacting Unreal, then retains
those exact bytes in `art/import-cache/<SHA1>/<Asset>.glb` for Unreal's Reimport source. Keep that cache.
It imports once into `/Game/Daedalus/Art/<Kind>/<Asset>`; `--dest` changes the parent folder and
`--name` asserts the expected asset. Unreal must be open and outside Play. The current import must
return its own mesh and material evidence, including material parents; an old destination asset
cannot make an empty import pass. ADR-055's project material repair and Nanite gate are preserved.

From code: `from asset_pipeline.ship_saved import ship_saved; report = ship_saved(job_path)`.
The CLI exits 0 for a passing report, 1 for a rejected shipment, and 2 for invalid input or an editor
failure. It does not update `QUEUE.md`, `feed.jsonl`, or the job manifest; queue integration remains
with the watcher. A timeout does not prove the editor cancelled the import: inspect before retrying.

## Harness

| Suite | What it proves |
|---|---|
| `harness/glb_test.py` | The `.glb` reader on hand-made files: indexed and non-indexed triangles, lines, instancing, and broken files refused (9 cases) |
| `harness/judge_test.py` | One good shipment passes, and each kind of loss fails exactly the check it should (14 cases) |
| `harness/ship_saved_test.py` | Saved manifest/file validation, retained snapshots, current-attempt evidence, Play refusal and ADR-055 material repair; offline fake editor, no live imports (37 cases, two real-link cases opt-in) |
| `harness/e2e.py` | Real Blender (`bpy`) exports and the Unreal stand-in imports the real `.glb`. Five planted losses (a mesh, a triangle, a slot, the units, the materials) are each REJECTED by the right check, and the CLI exit codes are checked (17 cases) |
| `harness/mutate.py --e2e` | Breaks the judge, the `.glb` reader and both editor scripts on purpose. Every break must turn a suite red. Results go to `ledgers/mutants.json` |
| `harness/run_all.py` | Runs every suite and prints n/m |
| `harness/shots.py` | Makes this README's screenshots from real runs, so they never go stale |

`e2e.py` finds the two connector repos as siblings of this folder, or you can pass `--blender-connector`
and `--unreal-connector`.

## Proven live

On UE 5.8.3 (Windows 11), the same three props went through a real Interchange import: **SHIPPED, 9/9 checks**
(`ledgers/live-ue58.json`). That run showed that Interchange makes one static mesh per object and bakes each
object's scale into it (the 2× crate is 200 cm). The reader, the judge and the stand-in now model that.

![The shipped props in the Daedalus level in Unreal](docs/images/unreal-live.png)

## Not verified here

The stand-in imports the way Interchange did live: one StaticMesh per object with its scale baked in, and a
bare mesh given the default material slot. Rotated objects are not size-checked exactly (only quarter turns). On a real UE 5.8 editor, run the CLI once and read the report. If
Interchange merges meshes or drops degenerate triangles, the judge will say REJECTED, and the report
shows where.

MIT
