# island_receiving_adapter (PROPOSED, R22 job 2, hephaestus)

This is a typed contract stub and contract tests for a future island production receiving adapter. It is built only from the existing
offline boundary (`island-continuation-source`) and the legacy `focused_native_islands_20261023` output shapes. For the field
mapping and the OPEN questions, see `docs/production/ISLAND-RECEIVING-ADAPTER-CONTRACT-PROPOSED-20261027.md`.

It is not adopted and has no production wiring. It does no I/O and makes no editor, broker or lease calls. `ProposedNativeAdapter` raises.

Tests (synthetic): `python -m unittest discover -s tools/unreal_preflight/island_receiving_adapter -p "test_*.py"`