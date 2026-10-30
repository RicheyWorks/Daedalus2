# DiskSaver Island: Rigging Check (G541)

Bosun Thaddeus walks the rigging of `.github/workflows` before the fleet sails.

`tools/streaming/rigging_check.py` reads every workflow as plain text (read-only, no YAML
library, nothing executed). Python dev tooling only; nothing runs inside Unreal.

| kind | severity | meaning |
|---|---|---|
| `unpinned` | error | `uses:` with no `@ref`, or a moving branch (main, master, HEAD, latest, dev, develop) |
| `major_drift` | advisory | action on a different major than the repo's most common one (ties go to the newest) |
| `third_party_tag` | advisory | action outside `actions/` and `github/` on a tag instead of a 40-hex commit SHA |
| `python_drift` | advisory | literal `python-version` that differs from the repo's most common |
| `no_permissions` | advisory | no top-level `permissions:` block |

Local `./` and `docker://` actions and `${{ }}` expressions are skipped. Repo-wide tallies
always cover every workflow; `--under PREFIX` keeps findings for workflows that use files
under that prefix.

Verdict: **taut** (no findings), **slack** (advisories only), **frayed** (any `unpinned`).

```
python tools/streaming/rigging_check.py --under tools/streaming
python tools/streaming/rigging_check.py --json --fail-on frayed
```

CI (`.github/workflows/rigging-check.yml`) runs the tests and gates
`--under tools/streaming --fail-on frayed`; the whole-repo survey is printed for information
only, so other lanes are never blocked. Hook: `data/islands/disk-saver/rigging-check-v1.json`.
