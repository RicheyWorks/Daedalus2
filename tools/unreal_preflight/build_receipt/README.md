# Plugin build receipt

Run right after a successful UBT link of DaedalusLink, before the editor relaunches. The receipt records the source
bytes and DLL that were actually built, so pinned consumers (producer guards, packaging pins) can be updated from a
build-time record. Before this existed, provenance had to be rebuilt after the fact (2026-10-26, rebuild 4 / R22c).

```sh
python tools/unreal_preflight/build_receipt/build_receipt.py write \
  --repo C:/Users/730ri/projects/Daedalus2-ueb-integrate \
  --plugin C:/Unreal/DaedalusRealm/Plugins/DaedalusLink \
  --dll C:/Unreal/DaedalusRealm/Plugins/DaedalusLink/Binaries/Win64/UnrealEditor-DaedalusLink.dll \
  --ubt-log <run>/ubt.log --backup-dll <backup>/DaedalusLink/Binaries/Win64/UnrealEditor-DaedalusLink.dll \
  --base <previous rebuild main sha> --out <run>/build-receipt.json
python tools/unreal_preflight/build_receipt/build_receipt.py verify --receipt <run>/build-receipt.json
python tools/unreal_preflight/build_receipt/build_receipt.py pins-diff --receipt <run>/build-receipt.json --pins <protected-files.json>
```

- `write` refuses (exit 2) without a `Result: Succeeded` line (UTF-16 and UTF-8 logs). For each `Source/**` file and
  the `.uplugin` it records the sha256, the git blob and whether that equals HEAD. It also records the merged PRs since
  `--base`, the DLL sha256/size/mtime, the old DLL and the log hash/line. `<receipt>.sha256` is the receipt's own hash.
- `verify`: exit 0 means no drift, 1 means changed/added/missing files or a different DLL, 3 means the receipt does
  not match its sidecar.
- `pins-diff`: read-only. It lists pinned rows under the plugin whose sha256 differs from the receipt
  (exit 1 if any). It never edits pins. Adopting new pins stays with each pin owner's reviewed procedure.

This is a post-link snapshot of what is on disk. `tools/build_evidence` (Codex) is the wrapper that observes a build
command from start to end; use it when the build itself is run through that wrapper.
