# Integration lessons

* Extend a format in all producers and consumers together. Native EGG and land
  additions exposed missing Java item/model/codec support through strict parity.
  Keep demo ownership explicit and separate from authoritative live deeds.
* Preserve random-stream consumption when a generated random reward becomes a
  fixed reward; otherwise unrelated later loot changes for the same seed.
* A shared catalog is not enough: compare actual C++/Java readers and test
  malformed refusals, then package the canonical resource rather than duplicate it.
* A new endpoint must enter the production posture audit and README table.
  Exercise refusal and authorized success against a booted production profile.
* Reuse the existing error handler. An empty 404 violates the API problem-detail
  contract even when status-only tests pass; run the generated-request audit.
* Test the executable classifier jar, not the thin dependency jar, and verify
  embedded resource bytes before booting an isolated packaged server.
* Export validation, visual acceptance, native linking and Play are different
  evidence stages. Preserve existing spreadsheet acceptance cells while appending
  assets; LODs and visual variants must not inflate distinct gameplay roles.
* Decimation can create invalid topology. Repair and verify a clean second pass,
  then validate exported indices, weights and animation loops.
* Use isolated Unreal scratch modules with supported hot-reload settings for
  compile checks, and release the editor turn. A scratch DLL does not prove the
  full shared plugin or a live scene.

### Dock round-trip verification
- Exercise remote boarding and exit together: original-character identity, visibility and collision must be checked after possession returns on both endpoints.
- An injected InputKey E event proves the engine binding and owner RPC path, not a physical keyboard or a rendered scene.
- A headless Unreal launch can generate DefaultInput.ini. Inspect it before changing it; this host already selected EnhancedPlayerInput/EnhancedInputComponent, so it was preserved.
- Keep production DLL/source proof before adding test actors. Fixture shutdown deliberately closes the connection; distinguish those messages from failures before the pass marker.

### Seeded Ocean terrain
- Reuse the existing chunk palette, save format and GLB exporter instead of introducing another terrain file format. Generate requested absolute-coordinate chunks; never allocate all lands just to bootstrap a sea sector.
- Save seed and generator version separately in realm metadata; the current voxel save does not record procedural generator provenance. Persist mined-to-empty area markers before adding live regeneration.
- Locale-dependent floating-point formatting can invalidate JSON. The exporter uses Locale.ROOT and was repeated under German locale; save and GLB bytes matched the original export.
- A generated sector is one terrain asset reference and zero character roles. Keep its Unreal status pending until actual import and Play proof exist.

### Ocean chunk persistence
- Read actual fallback behavior before reusing an atomic-save claim. Shared WorldStore can copy over targets after rename failures; Ocean writes to private staging first and requires an atomic final publish.
- A fully cleared chunk needs an explicit saved empty record. Treating no blocks as no record regenerates mined terrain on restart.
- An in-process overlapping-lock test is insufficient to prove OS writer exclusion. The separate-JVM probe verifies edits, empty records, competing writer refusal and reopen after release.
- Workbook recalculation may normalize a blank cached formula value from null to an empty string. Preserve formula text exactly and compare those two blank representations equivalently; do not relax comparisons of numbers or statuses.

### Ocean resident window
- Bound resident chunks and per-call warmup separately. A cache count bound does not establish a process-RAM, disk, frame-time or multiplayer-capacity budget.
- Save a candidate edit before publishing it in cache; on failed disk I/O retain the original cached state. Load before evicting so a corrupt destination does not discard useful data.
- A write-through cache has no unsaved dirty eviction queue. Keep snapshots independent and prohibit bypass writes while its store owns the directory.

### Ocean host API
- Reuse ChunkBlocksResponse so native meshing does not need a second block protocol. Authentication must precede any generation or disk access.
- Give sea chunk reads a distinct rate-limit bucket; sharing the maze-generation quota creates unrelated feature contention. Verify 429 and independent JWT-subject buckets over real production-profile HTTP.
- Default-disabled configuration is separate from production authorization. Development permitAll does not supply a JWT decoder; fail closed and use the production resource-server setup for authenticated access.
- Distinguish an opt-in sector endpoint from world registration and native realm loading. HTTP/restart proof does not establish a visible dock transition.

### Native Ocean transport
- Prove the real boundary: run the packaged production Java server against the native engine HTTP component, not only a JSON fixture or mocked transport. Record startup-inclusive timing separately from native test-body time.
- Keep bearer tokens out of reflected/config/replicated properties, command arguments and logs. The private probe uses fresh short-lived credentials in child environments and checks logs before recording hashes.
- A final response URL check does not prove safe redirect credential handling. Keep TLS/redirect policy and rendered travel as explicit open gates after successful loopback transport.
- Bound streamed response bytes before accumulating them; validate exact chunk identity, canonical payload length and palette indices before publishing a result. Cancel and invalidate session generations on both destruction and EndPlay.

### Native Ocean geometry and cleared revisions
- Generate palette metadata from the existing Java canonical tables and check drift; do not hand-maintain another colour/visibility table.
- Mesh chunks in local coordinates and use double component offsets. This preserves local geometry at distant plots and avoids global signed mesher boundary arithmetic.
- Empty data still has a revision. Persist the explicit empty chunk rather than dropping it from the snapshot, or a restarted server can send an older revision that native stale-update guards refuse. Store replacements now reject older or same-revision conflicting payloads.
- Verify the boundary with a separate Java writer, packaged server reader and native scene consumer. The private fixture proves a persisted clear removes old geometry; NullRHI geometry/collision flags are distinct from rendered appearance and physical walking acceptance.

### Ocean art and rendered inspection
- Use explicit UTF-8 and LF for generated cross-language tables. Windows default encoding changed a source hash even when palette semantics stayed the same.
- Unreal single-input material nodes can expose an unnamed pin. Check every material connection and compilation result rather than treating a saved asset as a compiled material.
- Rescan the plugin asset registry before repeat commandlet imports. Mark lights and inspection backdrop components movable before changing their transform or mesh.
- Hide the default spectator pawn when capturing through a staged camera; otherwise its sphere can obscure the artwork.
- Inclusive voxel coordinates describe occupied cells: x=-6..6 spans 13 metres and has centre x=0.5. Fit decorative meshes to those physical extents without silently changing collision.
- Blender tessellation indices can vary between equivalent exports. Freeze accepted GLB bytes when adding unrelated assets and record their source hashes instead of claiming byte-identical regeneration.
- A rendered inspection proves appearance in that private scene. It does not establish controls, collision fitting, cross-realm loading, cooking or shared-world acceptance.

### Configurable Ocean body collision
- Fit the navigation body explicitly; a skiff's sail or submarine's periscope should not silently enlarge its navigation box. Keep decorative geometry distinct from the documented collision profile.
- A server-side box resize needs bounds, occupancy and blocking-overlap checks before publishing any change. Replicate the accepted dimensions and apply them to the remote component in OnRep; replicating a numeric property alone is not proof that collision changed.
- Verify wall sweeps in native physics and separately observe the actual remote box dimensions and client refusal through a real server/client pair. Keep rendered navigation and rotation clearance open until tested.
- Inspect cross-team code before relying on a broadcast's event-order description. The realm notification/save ordering differed from the initial handoff; report the exact discrepancy to the owner before wiring dependent transitions.

### Actual HTTP destination and build serialization
- UE GetURL retains the request URL after redirects. Verify GetEffectiveURL with case-sensitive resource-path matching and test actual transport against direct, path, port and path-case endpoints.
- A refused redirected payload does not prove that transport withheld credentials. Record observed forwarding separately and retain the production transport gate.
- Even private Unreal startup invokes Build.bat platform validation. Serialize private probes and compilation with the compute lease; a startup waiting on another build is not a failed HTTP scenario or a reason to restart a live build.

### Live team handoff recovery (2026-10-13)
- An acceptance mentioning two request IDs in prose left both tracked requests overdue because reply_to was null. Send one correlated event per request; the batch respond command makes that one explicit agent action without inferring acceptance from text.
- Check the actual listener and health endpoint when delivery fails. Port 9890 had no listener during this check. Restarting the existing deployed broker against its original log restored last ID 28979; retrying the saved request envelope delivered ID 28980. No history reset or alternate broker was needed.
- Preserve request UUIDs before network calls. A response batch can be interrupted after its first delivery; tests must prove replay creates exactly one event per request and invalid batch members prevent any send.
- Durable receipt is not live agent participation. Poll during active tool/job loops, report authoritative terminal job results promptly, and keep agent acceptance separate from transport recovery. Claude's correlated rollout acceptance remains outstanding at this checkpoint.

### Discover providers without duplicating terrain
- The same chunk DTO does not make two storage providers interchangeable. WorldHub mounts WorldService files; Ocean owns its own persistent window. Advertise each provider's existing routes rather than mounting a second copy of its data for discovery.
- Refuse duplicate canonical realm IDs instead of selecting whichever provider was listed last. Keep protocol and write capability explicit; a supported operation still requires the caller's permissions.
- A metadata request must not generate chunks or mutate the world registry. Test that invariant before following a discovered route in a real authenticated HTTP test.
- Add new endpoints to the production matcher, independent authentication table and published README together. A passing default authentication rule alone does not document the intended decision.
- Storage world IDs, native session IDs and catalog stems are distinct. Publish optional canonical bindings server-side, require matching shipped aliases/styles, leave custom worlds unbound, and refuse duplicate session claims. Do not infer a player's game from a storage style or promise that a referenced catalog is installed.
