# DiskSaver Island: Leading Lights (G543)

Lightkeeper Seraphine checks that every page in the harbour library still points somewhere real.

`tools/streaming/leading_lights.py` reads every `*.md` file in the repo (read-only, no network).
Python dev tooling only; nothing runs inside Unreal.

| kind | severity | meaning |
|---|---|---|
| `broken` | error | a relative link or image target does not exist |
| `missing_anchor` | advisory | the target exists but has no heading for its `#anchor` (GitHub slug rules, duplicates get `-1`, `-2`) |
| `local_path` | advisory | a link to one machine's disk (`C:\`, `file:`, `~/`) |
| `outside_repo` | advisory | a relative link that climbs out of the repo root |
| `stale_path` | advisory | an inline-code repo path (for example a tools or docs file) found neither from the repo root nor from the page's folder |

Web links are never fetched. Fenced code blocks and inline code are not treated as links. A
leading `/` means the repo root. `.git`, dot-folders, `node_modules`, Unreal build folders and
`__pycache__` are skipped. `--under PREFIX` keeps only files whose repo path starts with PREFIX.

Verdict: **lit** (no findings), **dim** (advisories only), **dark** (any `broken`).

```
python tools/streaming/leading_lights.py --under docs/islands
python tools/streaming/leading_lights.py --json --fail-on dark
```

CI (`.github/workflows/leading-lights.yml`) runs the tests and gates `docs/islands` and
`tools/streaming` with `--fail-on dark`; the whole-repo report is information only, so other
lanes are never blocked. Hook: `data/islands/disk-saver/leading-lights-v1.json`.