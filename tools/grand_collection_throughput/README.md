# grand_collection_throughput

Read-only. `extract` measures per-chunk stage seconds (blender, pre, import, validate, post, gap) from files the
Grand Collection run already writes (SourceJobs start/terminal, chunk asset and .umap mtimes, CatalogChunks CSV)
and the editor log. `simulate` fits each stage per editor session (start + drift per chunk) and projects hours to a
target under speed-up options (Blender pipelining, incremental pins/hash, validate new items once, incremental
catalog export, 20 per kind, editor relaunch interval). Option factors are stated assumptions in `OPTIONS` /
`PER_ITEM`; measure the real effect with the acceptance test in BOARD GRAND-COLLECTION-THROUGHPUT-PLAN-20261026.md.
It never touches the producer, editor, leases or Codex's scripts.

    python tools/grand_collection_throughput/throughput_sim.py extract --campaign <GrandCollectionR18> --content <Content/.../NativeDiscovery/20261024> --log <Saved/Logs/DaedalusRealm.log> --from 150 --to 240 --out stages.json
    python tools/grand_collection_throughput/throughput_sim.py simulate --stages stages.json --saved 2400 --target 10000 --md projection.md