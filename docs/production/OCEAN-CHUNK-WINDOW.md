# Ocean resident chunk window

OceanChunkWindow owns an OceanChunkStore and its single-writer directory lock.
It keeps 1..4096 resident chunks in access order, evicting the least recently
used when capacity is reached. Reads and mutations use existing absolute block
coordinates, including negative axes. Chunk snapshots are independent copies.
The capacity bounds this cache's resident chunk count, not process RAM, external
snapshots, mesh memory, disk use or total player count.

Edits use write-through storage: copy the cached chunk, change the copy, save
through the staged/atomic chunk store, then publish the new cached value. Failed
saving leaves the original cached chunk unchanged. Loading completes before
another resident is evicted, so failed loads do not discard useful cached data.
All cached edits have already reached the store; eviction needs no dirty queue.
Unchanged block writes skip the save. Close releases the writer lock.

warmAround touches a nearest-first capacity-sized subset of a bounded box.
Horizontal radius is 0..8 chunks, vertical radius 0..4, and each call permits
0..64 new loads. Cache hits do not consume the load budget. Ties sort by x/y/z.
Signed-coordinate edges filter unavailable neighbours rather than overflowing.
The calls perform synchronous disk I/O: hosts must use their own worker/ticket
scheduler, request quotas and player-range checks, not run disk warmup in Unreal's
frame loop. This is a host cache, not a replicated visibility policy or completed
multiplayer streaming integration.

Validation: 18 focused Ocean tests and all 718 core tests passed. Tests cover
80-chunk traversal with four residents, edit eviction/reload/reopen, nearest-first
loading budgets, negative coordinates and signed edges, read-copy isolation,
failed-save cache preservation, failed-load non-eviction and lifetime ownership.
Separate JVMs also traversed 20 chunks at capacity three, retained an edit through
eviction and process restart, verified competing writer exclusion and reopened
after release. The process probe took 4.031 seconds including Java source launch;
this is not a gameplay frame-time or server-capacity benchmark.

Evidence is ocean-window-proof.json. The existing Windows/Ubuntu Ocean CI runs
the updated full core suite and process probe. WorldHub/WorldService, authenticated
endpoints, district ownership, Unreal realm switching, visible scene import and
public hosting are still integration requirements, with no shared owner files
changed here.
