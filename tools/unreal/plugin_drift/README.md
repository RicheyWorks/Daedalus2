# plugin_drift: keep installed Unreal plugins matching the repo

Two small read-only tools (Python 3.8+, standard library only):

- `plugin_drift.py` compares an installed UE plugin folder (for example `C:\Unreal\DaedalusRealm\Plugins\DaedalusLink`)
  with the repo copy (`engines/unreal/DaedalusLink`). It matches by relative path and SHA-256, and
  sorts every file as `identical`, `eol_only` (same once CRLF/LF are normalised), `differing`, `live_only` or `main_only`.
  It writes a `plugin-drift/v1` JSON manifest plus a Markdown summary and exits 1 when there is drift (0 clean, 2 error).
  `Binaries/`, `Intermediate/`, `Saved/`, `DerivedDataCache/` are skipped.
- `secret_scan.py` runs before every push. It flags credential-looking content and forbidden files
  (`.env`, `*.key`, `*.pem`, `relay-webhook*.json`, anything under `Saved/`, `Intermediate/`, `Binaries/`)
  and prints **path:line rule only, never the value**. Exit 1 on any finding. If gitleaks or detect-secrets is
  installed, run it as well; this script is the floor.

**How it fits Daedalus:** every island's native code ships in the one DaedalusLink plugin, so this checker keeps the
native code running in the live world matching the canonical repo. Drift shows up as a manifest, never as a surprise
at the next build.

```powershell
python tools\unreal\plugin_drift\plugin_drift.py --live C:\Unreal\DaedalusRealm\Plugins\DaedalusLink `
  --repo engines\unreal\DaedalusLink --repo-ref (git rev-parse HEAD) --label DaedalusLink `
  --json docs\production\drift\daedalus-link.json --md docs\production\drift\daedalus-link.md
python tools\unreal\plugin_drift\secret_scan.py --root . --base origin/main   # before every push
python -m unittest discover -s tools\unreal\plugin_drift -p "test_*.py"
```

Neither tool writes to the live project, starts the editor or builds anything. Reconciling drift (copying files into
the live plugin, rebuilding, restarting) belongs to the sole Unreal writer and goes to them as a NEED packet.
