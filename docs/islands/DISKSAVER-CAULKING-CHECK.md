# DiskSaver Island: Caulking Check (G544)

Caulker Evander runs his thumb along every seam of the lane's text files.

`tools/streaming/caulking_check.py` reads the bytes of text files (read-only) and checks the
seams, not the meaning. Python dev tooling only; nothing runs inside Unreal.

| kind | severity | meaning |
|---|---|---|
| `bad_utf8` | error | the file is not valid UTF-8 |
| `bad_json` | error | a `.json` file, or a `.jsonl` line, does not parse |
| `duplicate_key` | error | a JSON object repeats a key; `json.load` keeps only the last one, silently |
| `bom` | advisory | starts with a UTF-8 byte-order mark |
| `crlf` | advisory | CRLF line endings (count; `mixed` when LF lines are present too) |
| `no_final_newline` | advisory | non-empty file without a final newline |
| `trailing_space` | advisory | lines ending in spaces or tabs (not checked in Markdown, where two trailing spaces mean a line break) |
| `tab_indent` | advisory | `.py`/`.yml`/`.yaml` lines indented with a tab |

Extensions: `.py .md .json .jsonl .yml .yaml .txt .toml .csv .ini .ps1 .sh .cfg`. `.git`,
dot-folders, `node_modules`, `__pycache__` and Unreal build folders are skipped. `--under`
(repeatable, folder or file) picks the lane; the default is `tools/streaming`,
`data/islands/disk-saver` and `docs/islands`.

Verdict: **sound** (no findings), **weeping** (advisories only), **leaking** (any error).

```
python tools/streaming/caulking_check.py
python tools/streaming/caulking_check.py --under data --json --fail-on leaking
```

CI (`.github/workflows/caulking-check.yml`) runs the tests and gates the default lane with
`--fail-on leaking`; nothing outside the lane is checked, so other lanes are never blocked.
Hook: `data/islands/disk-saver/caulking-check-v1.json`.
