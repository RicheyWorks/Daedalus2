# Cast binding audit

The editor owner can capture `daedalus_binding_dump.capture()` through the existing Python bridge while PIE is stopped. Save its returned JSON as the night-run registry dump. This new capture reads loaded Talkers and registry records; it never scans, imports, loads assets, saves maps or rebinds actors. Native `ArtIds()` supplies candidate order, avoiding another alias resolver.

```powershell
python tools/realms/check_bindings.py --dump binding-dump.json --out binding-gaps.json
```

Optional `--expected-casts PATH` reads `who` declarations in that scoped DCS folder and reports roles not observed in the loaded world. Supply only the intended realm's files if other realms are unloaded. Exit2 means gaps or observation errors; exit0 requires at least one observed role and consistent binding observations for every captured role. Output uses exclusive creation and records the input SHA256.

Statuses distinguish missing art, a selected folder lacking a skeletal mesh, available art not bound, and inconsistent native binding state. Importantly the native resolver stops at the first alias containing any asset: an earlier material-only folder shadows a later mesh folder. The auditor reproduces that selection rule instead of treating any alias with a mesh as success.

An existing skeletal mesh, native `has_art`, `art_found` and the component's actual mesh path must agree before `bound-observed`. These observations do not prove rendered quality, animation playback, quest behavior, unloaded actors or packaged availability. The capture is non-atomic and rejects a world change/PIE start detected at its end. Runtime collection and real property exposure remain for the editor owner's next job boundary; offline fixtures prove only report classification.
