# r22_chunk_reconcile (PROPOSED, R22 job 1, hephaestus)

Read-only checker that a chunk-314 recovery neither loses nor double-counts a chunk. See
`docs/production/R22D-CLOSEOUT-RECOVERY-REVIEW-20261027.md`.

```
python reconcile_chunks.py before  --ledger <ledger.json> [--chunk 314 --next 3241 --per-kind 3240]
python reconcile_chunks.py across  --before <copied pre-recovery ledger> --after <ledger.json>
python reconcile_chunks.py session --dir <old R22c session folder>
```

Reads only the named files. It never writes, renames, locks, calls a broker or the editor, or edits pins. It is a proposal for
Boss and is not wired into any run. Tests (synthetic only): `python -m unittest discover -s tools/unreal_preflight/r22_chunk_reconcile -p "test_*.py"`.