# Reproducible Image Optimizer fixture

Evidence-only harness for Image Optimizer PR5 at `bdd47836cedb5c5261d281cb4ab132a1e89fcb91`. It invokes the existing app's approved-workspace service and encoder; it does not rewrite the protocol, choose personal files, automate a GUI/native client, touch the editor, install software, download dependencies or contact external services.

Requirements: PowerShell, Git, JDK 21+ (`java`/`javac` on PATH), the exact app checkout, and an already cached Thumbnailator 0.4.20 JAR with SHA-256 `3f64835132076ba7d01e2780747eb2304f67f296cfb71729af3bdbdae71eab3a`. Source head, all eight Java source blobs, resources and dependency hash are checked before execution. Compilation and runtime each use a 128 MiB heap. Outputs go only into the explicit evidence directory, apart from bounded generated app-private temporary storage rooted there.

```powershell
$inputs = @{
    AppRepo = '<local image-optimizer PR5 checkout>'
    CachedThumbnailatorJar = '<already-cached thumbnailator-0.4.20.jar>'
    EvidenceRoot = '<new local test-owned evidence folder>'
}
.\Run-ImageAcceptance.ps1 @inputs -Mode compile
.\Run-ImageAcceptance.ps1 @inputs -Mode serve-smoke
```

Modes:

- `compile`: compile exactly eight unchanged app sources plus the runner into the evidence folder; record provenance. No implicit compilation occurs in other modes.
- `run`: generate four nested PNG/JPEG fixtures, approve their frozen plan programmatically, check actual HTTP conversion, exports, source hashes, duplicate/skip behavior, revocation and retained outputs. Use a fresh evidence folder; retain it for the following mode.
- `verify-persisted`: verify the preceding `run`'s source/output hashes in a fresh JVM. Committed-file persistence is tested; durable grant/job history is not claimed.
- `serve-smoke`: briefly start the actual service on a new literal-loopback port, create an owner-only transient pairing file, read capabilities/plan, revoke and close. It verifies link deletion and connection refusal after shutdown.
- `serve`: approve only one newly generated alpha PNG and expose its actual workspace service for an operator-owned native pairing check. It uses port 0 on `127.0.0.1`, a fresh 90-second grant and one owned `live-fixture-<uuid>` directory. The private link is in owner-only `pairing-link.txt`, never stdout; `ready.json` contains no token. Native revoke or an empty `stop.request` file ends the fixture early. Normal cleanup removes the link; already committed images remain. The process self-stops within the 90-second grant plus bounded normal cleanup, below 120 seconds. Force-kill cleanup is not claimed.

For `serve`, prepare the existing **ADaedalusApprovedWorkspaceTerminal** with Application **ImageOptimizer** first. Paste the fresh `/realm/image-workspace/#token=...` link, choose **Pair approved workspace**, verify the one-input frozen settings, choose **Start / retry same approved action**, then **Refresh actual progress**. The app writes `approved-output/synthetic-alpha.png` as 64×32. The native panel has no download button. After uncertainty, Refresh discovers the existing action; do not create a new plan/key automatically. Revoke when finished. This harness's programmatic fixture approval is distinct from a user approving files through Swing. No native/GUI/Play acceptance is implied by a service test.

`ImageWorkspaceAcceptance.java` is an unchanged copy of the locally tested fixture runner. The portable wrapper requires explicit paths and never starts a GUI or native app automatically. The caller remains responsible for the existing local-loopback execution policy; no new account, credentials or external service permission is needed.
