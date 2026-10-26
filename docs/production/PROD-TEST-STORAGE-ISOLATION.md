# Production-profile test storage isolation

The 2026-10-13 Labyrinth verification passed but exposed a real fixture problem:
production-profile tests loaded `C:/Users/730ri/.daedalus/worlds.registry` and
started ecology ticks against existing developer worlds. The run logged
`Ark harbour tick failed` / `Cannot persist ecology ... bricks.daew.ecology`.
Several cached Spring contexts could therefore access the same real files.

All five `@ActiveProfiles("prod")` Spring integration tests now install an
`IsolatedWorldStorage` dynamic property before constructing the world host.
The test-only helper allocates a fresh OS temporary directory per context,
captures one stable `world-zero.daew` path, and binds `daedalus.world.file` to it.
WorldHub's registry and world sidecars stay beside that file, away from developer
saves and other test contexts. Temporary files remain in the OS temp directory
for inspection; this change does not delete any developer data.

The production boot test additionally verifies that the actual injected world
service points to the fixture directory, has no inherited chunks, and mounts
only World Zero. Authentication, WebSocket handshake and static-surface tests
retain their existing production profile and assertions. Production defaults,
the ordinary test profile and explicitly configured restart fixtures are
unchanged.

Focused verification:

```powershell
mvn -B -pl daedalus-server -am test '-Dtest=ProdProfileBootTest,ProdAuthPostureTest,ProdStaticSurfacePostureTest,TacticsHostAuthorizationTest,WebSocketProdHandshakeTest' '-Dsurefire.failIfNoSpecifiedTests=false'
```

This repairs observed test isolation, not public hosting or Unreal runtime
acceptance. Broader test-profile temporary-file sharing remains a separate
potential improvement; these five production contexts no longer inherit the
developer's world directory.
