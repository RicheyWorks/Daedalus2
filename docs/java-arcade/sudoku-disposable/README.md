# Disposable Sudoku service verification

Source pin: `RicheyWorks/sudokupro` commit
`973c73a35f8659a17022232f0996d4ffb0095997`. Production sources were unchanged.
The copied [proof](proof.json) records **27 real JDK HTTP/WebSocket checkpoints**
in one passing targeted JUnit test, Maven offline exit 0, on installed JDK 21.0.4.

This booted owned embedded Tomcat on a random `127.0.0.1` port with the real dev
`SecurityConfig`, JPA/domain code and disposable H2 memory storage. All regular
and reactive Redis/Jedis/relay beans were mocked before startup; FCM was disabled.
Inherited database, Redis, Spring, admin, FCM and Java/Maven override families
were removed in the owned runner process. Synthetic accounts/data were used.
No existing credentials, services, databases, game source or saves changed.

Actual checks covered Basic/CSRF authentication, visible 81-cell state with no
solution, own/spectator mutation permissions, moves/undo/redo/erase, clue
protection, hint response and measured **one hint / five virtual gems**, explicit
save/list/resume, single-use tickets, competitive refusal, expiry and synthetic
password revocation of old HTTP/socket access. The disposable-only time-attack
setting was one second; production defaults were unchanged. An invalid/reused
ticket can upgrade and then close with code 1008, rather than necessarily fail
the HTTP handshake. The native client already treats that close as permanent.

The test closes its owned listener; the runner exits its JVM. Independent
read-only checks confirmed PID 61556 absent and port 56484 without a listener.
Earlier failed harness attempts are retained in the task folder as failed
diagnostics and are not counted as passes. The expected mocked-Redis scheduler
diagnostic does not establish scheduler/Redis acceptance.

## Reproduce in a disposable source copy

Use the exact source pin in a separate owned copy. Copy
[DisposableLoopbackSmokeTest.java](DisposableLoopbackSmokeTest.java) to
`server/src/test/java/com/xai/sudokupro/` and
[run-disposable-smoke.ps1](run-disposable-smoke.ps1) to that copy's root.
Run it in a **new PowerShell process**, so its temporary environment sanitization
does not alter a caller's interactive shell:

```powershell
pwsh -NoProfile -File .\run-disposable-smoke.ps1
```

Prerequisites are the already installed JDK 21.0.4, Maven 3.9.9 and cached source
dependencies. The runner uses offline Maven and installs nothing. It executes
only the targeted test with a bounded fork timeout. The real production service
still requires its PostgreSQL/Redis/Flyway setup and account/runtime provider.

The executed original harness SHA-256 was
`1F8E92DDBA36E39D6A20C6A2A291E4427E449F882FAA23CB2A70F78773D56934`.
The repository copies normalize trailing whitespace; this does not change test behavior. Proof metadata records the executed original local artifact bytes; Git may normalize text
line endings. This smoke does not prove real PostgreSQL/Redis, scripts,
cross-replica behavior, Unreal parsing/callbacks, plugin loading, packaged or
in-world play.
