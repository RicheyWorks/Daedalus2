# Bounded synthetic Photo companion fixture

This tooling targets the notice-complete `PhotosToPDFPC` PR 4 application at
`8311880587461f39bcde22234d05738d8a590de9`. It starts the real packaged bridge,
generates two tiny red/blue PNG/JPEG inputs, and can freeze only those generated
files into an approved workspace. It changes no application code or CLI.

Provide an explicit cached Windows x64 JDK 21+ `bin` directory and the application's
already cached runtime JAR classpath. No JDK, dependency or service is downloaded.
The application JAR must occur **exactly once**, with SHA-256:

```text
6c5fe36af905f8f2ef5d02bc50d7dc648da439bc00ea94db0f90ce331e2b0e12
```

This is the application entry inside the tested notice-complete Windows ZIP.
The wrapper rejects another application identity and places this pinned JAR
before the remaining libraries. Other explicit cached JAR hashes are recorded.

```powershell
# Set these to explicitly approved local cache/output paths for this machine.
$JavaBin = Split-Path (Get-Command javac).Source
$ClasspathFile = './local-cache-classpath.txt'
$EvidenceRoot = './new-photo-fixture-evidence'
& './Start-PhotoFixture.ps1' -ClasspathFile $ClasspathFile `
  -JavaBin $JavaBin -EvidenceRoot $EvidenceRoot `
  -Mode selected -RunName 'photo-native-01' -Seconds 120
```

The classpath file contains one semicolon-delimited cached JAR classpath; use
`-CachedClasspath` instead to provide it inline. No personal-home path is assumed.
`EvidenceRoot` must be new, with an existing parent and no reparse parent aliases.
The wrapper compiles only `PhotoFixtureLauncher.java` into that output directory.

Modes are `selected`, `workspace`, `a4-portrait` and `a4-landscape`. The latter two
explicitly select the newly exposed merged legacy A4 layout, separate from the
original one image-sized PDF per photo. `workspace` preserves that original
individual layout at the previously frozen generated-output destination.

Requested duration is 1..120 seconds. The effective service window is capped at
**110 seconds**, measured from launcher entry, with ten seconds reserved for
normal cleanup; the selected bridge may await its worker for five seconds. Each
listener binds an exclusive literal `127.0.0.1` ephemeral port, with no fixed-port
dependency. JVM heap caps are 128 MiB for compilation and 192 MiB for the service.

While running, the fresh owner-only capability file is:

```text
<EvidenceRoot>/runs/<RunName>/private-pairing-link.txt
```

Copy its contents directly into the matching native password field; never print
or commit the capability. It is removed on normal close. Removing that exact file
requests an earlier normal stop; no process kill is used. Generate a new run/link
after expiry. Generated chooser inputs are under `runs/<RunName>/inputs/`; the
workspace destination is `runs/<RunName>/approved-output/`.

`selected` links have `/#token=…`; workspace links have
`/realm/photo-workspace/#token=…`. The workspace link identifies a native API,
not an HTML chooser page. The fixture checks one authenticated capabilities GET
but does **not** automatically create sessions, submit images or start conversion.
Those actions must be explicit in the native UI.

On exit, `command.json`, compile/runtime logs and the run's `lifecycle.json`
retain commands, cache hashes, capability-check result and observed post-close
connection refusal without the secret. Evidence is never overwritten.

This is synthetic fixture approval and protocol tooling. It does not establish
installed JavaFX chooser behavior, valid native/Unreal pairing, file-dialog export,
hardware, reboot durability, credentials, email, fax or external-service behavior.
Run the actual UI acceptance only through the operator's approved editor workflow.
