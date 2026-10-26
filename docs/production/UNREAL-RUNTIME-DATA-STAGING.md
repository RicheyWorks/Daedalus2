# Runtime text data in packaged Unreal builds

The Hero reads `Content/Inventory/*.dic` and `Content/Realm/realm-7.drr` with
`FFileHelper`; Talkers read `Content/Casts/*.dcs`. These files exist beside the
plugin in an editor checkout. Before this change, the plugin Build.cs had no
runtime dependency declarations for them. Editor file-load success therefore
did not establish that a packaged build would contain the same data.

`DaedalusLink.Build.cs` now declares the three file families as UFS runtime
dependencies. Wildcards include new catalogs and casts without a separate
staging list. Existing optional `Realm/*.dsp` sprite packs are included when
present. Editor Python, source CSV files, saves and credentials are not added.
The runtime readers and their paths are unchanged.

Epic documents `RuntimeDependencies` for staging additional files and UFS for
files accessed through Unreal's file APIs, including PAK storage:
[Epic's runtime dependency documentation](https://dev.epicgames.com/documentation/unreal-engine/integrating-third-party-libraries-into-unreal-engine).

## Actual rule evaluation

An isolated host was created using the existing `full_plugin_host.py`, with
every one of the 171 tracked plugin files copied and hashed from source
`19ce237002b343bee2dd8ca75f1e32a8b38e6131`. No overlay or live installation was
used. UnrealBuildTool 5.8 ran `-Mode=JsonExport UnrealGame Win64 Shipping` against
that host, without code-generation actions, a compiler job, cook or editor.
It exited 0 in 3.93 seconds and exported all three UFS declarations for the
linked DaedalusLink module. Two existing RawInput deprecation notices remained.

The `verify_runtime_data.py` tool checks that actual exported module data against
the exact snapshot hashes. Ten files are covered on the current main baseline:
five inventory catalogs, four casts and the retro realm. Ocean's sixth catalog
is in PR93 and will be matched by the same inventory wildcard when integrated.
The verifier neither counts a wildcard as an asset nor labels this as a
successful packaged launch.

```powershell
python tools/unreal/verify_runtime_data.py C:/isolated-host C:/isolated-host/shipping-target.json --output proof.json
python tools/unreal/test_runtime_data.py
```

Six verifier regressions cover wildcard expansion, the old empty declarations,
an omitted runtime family, changed snapshot bytes, unintended editor Python,
and an incorrect staging type. They run in Engines CI. Actual UBT evaluation
still requires an installed Unreal Engine; ordinary hosted CI is not a proxy
for it.

## Remaining shipping acceptance

`unreal-runtime-data-proof.json` records the evaluated declarations and file
hashes. This proves Shipping build-rule configuration, not the final staged
archive. A cooked client must still be staged, launched away from the source
checkout, and exercised for inventory, dialogue, retro realm and optional
sprite loading. That acceptance belongs to the shared Unreal operator and
must include runtime logs and visible gameplay. No editor session was opened
or modified for this change.

## Actual native project adoption and archive — 2026-10-14

Native source Build.cs now has the reviewed three UFS declarations; Shipping JsonExport changed from zero runtime dependencies to three wildcard families covering five DICs, five DCSs and one DRR. The existing native DRR has34land rows versus the older branch's3 and is preserved byte-for-byte; it independently matches published50b55d15/3ba94ab9 (SHAa48de4b...). Initial absence inference from formatted shell output was incorrect. No canonical-data replacement occurred. The adoption receipt records this correction and an initial failed lease command/wrong working directory; lease was acquired before further reconciliation. Multi-command shell status must not hide an earlier failed assertion.

Actual target is DaedalusRealm, not genericUnrealGame. Generic target succeeded with one metadata action only; actual DaedalusRealm Win64 Shipping compiled/linked66actions in292.71seconds, producing170,653,696bytegame EXE (SHA7dac18b7...). RawInput and cloud API deprecations remain warnings. This action used one compiler action at a time as a finite job option, no persistent resource policy or editor restart.

First normalUAT cook stopped before child launch on missingDaedalusRealmEditor.target. InstalledProjectParams supports `-unrealexe`; existing UnrealEditor-Cmd.exe was selected without fabricating a receipt or rebuilding the open editor. Actual cook then failed25after488.01seconds on missingGameFeatureData rules. InstalledGameFeaturesEditorModule's normalrepair specifies nativeGameFeatureData AlwaysCook. Native Config/DefaultGame.ini now contains that additiveproject rule; no engine-global/security/guard settings changed. `setup-unreal.ps1` reproduces the rule through existing Set-IniValue, preserving other/inherited array scans and existingcustom GameFeatureData entries. Isolated config-helper checks pass on PowerShell7 andWindowsPowerShell5.1; the installer was not rerun. WindowsCI exercises these helpers.

The normal iterativecook/stage/pak/archive subsequently exited0 in166.76seconds, processing13,259packages. Archive: `C:/Unreal/DaedalusRealm/Saved/Packages/WZ-20261014-native/Windows`. Native UAT logs remain local, not committed with machine metadata. Actual UnrealPak filtered extraction returned0; all11rawruntime files match the currentmanifest SHA256 and lengths, including the34land DRR. This is payload proof, distinct from earlier declarations. Five archivecontainer hashes/sizes are retained in native-package-payload-proof.json; uasset data uses IOStore, nonasset data is in the PAK.

Retained evidence: native-runtime-staging-adoption.json, native-shipping-build-proof.json, native-asset-manager-fix.json and native-package-payload-proof.json. Packaged game launch, actual runtimefile loading, walking, authoritativeownership/persistence andpublichosting remain unproven. No mint, public deployment, servicecredential changes, editorrestart or broadPlay were performed.
