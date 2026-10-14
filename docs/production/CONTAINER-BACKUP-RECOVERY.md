# Container backup recovery acceptance

PR95 demonstrates image startup and runtime resource availability. This next
acceptance step exercises the actual world backup format and saved changes.
It is stacked on `codex/container-runtime-resources` so the existing working
image build and HTTP helpers are reused.

`tools/deploy/container_recovery.py` creates uniquely named source and target
volumes and disposable production-profile containers. It uses generated test
JWT credentials and ephemeral loopback ports. Through existing authenticated
HTTP routes it creates Gallery and Parcels worlds, claims one plot in each,
and places distinct blocks in those plots and World Zero. It records the actual
world IDs, styles, signed seeds and titles.

The source container is stopped before the existing `deploy/backup.sh` archives
its volume. Redis is represented only by an empty temporary directory. The
archive is extracted into the separate target volume. The restored production
server must report the same world metadata, all three saved blocks and both
plot claims. Every mutation response must explicitly report `PLACED` or
`CLAIMED`; an HTTP 200 containing `DENIED` cannot pass.

Run with a locally built image and a fresh output directory:

```sh
python3 tools/deploy/container_recovery.py --image daedalus-resource-smoke --output recovery-proof
```

The tool refuses an existing output directory, never calls the live
`restore.sh`, and only removes its own newly named containers and volumes.
It retains the synthetic archive, redacted source/restored logs and, on success,
`proof.json` with image identity, archive hash, checked state and elapsed time.
The Container runtime resources workflow builds the actual image and runs this
test, publishing `container-recovery-proof` separately from the resource smoke.

Local Python compilation is checked. Actual recovery acceptance requires a
successful container job; the Windows development host currently has no running
Linux Docker daemon. This check does not prove Redis recovery, concurrent live
backup consistency, every sidecar, public infrastructure or Unreal gameplay.
Those requirements remain open even after a successful synthetic recovery.
