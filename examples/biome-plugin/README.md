# Daedalus example plugin — `biome-plugin`

Worked example for the [Writing a plugin](../../README.md#writing-a-plugin)
section. Registers two themed generators and subscribes to
`MazeGeneratedEvent` to log a one-line summary per generation.

## What it adds

- **`forest-biome`** — recursive backtracker with a vertical-first direction
  bias. Visually evocative of long trunks with short side branches.
- **`desert-biome`** — Sidewinder variant with widened runs (1/3 close
  probability vs. Sidewinder's 1/2). Long horizontal "dune" corridors.
- An `ApplicationListener<MazeGeneratedEvent>` that logs
  `[biome] maze generated id=... gen=... dims=... seed=... visited=... backtracks=...`
  for every generation the host emits.

Both generators produce perfect mazes (single connected component, no
cycles), are seed-deterministic, and have unit tests in
`src/test/java/com/daedalus/examples/biome/BiomeGeneratorsTest.java`.

## Build

The example is **deliberately not** part of the main reactor — `mvn clean
verify` at the repo root only builds the five production modules. To build
the plugin JAR:

```bash
mvn -f examples/biome-plugin/pom.xml clean package
```

The output lands at:

```
examples/biome-plugin/target/daedalus-biome-plugin-1.0.0-SNAPSHOT.jar
```

## Run it against the server

The `examples/run-with-biome.sh` helper rebuilds the plugin, copies the
resulting JAR into a temp plugin directory, and boots the server pointing
`daedalus.plugins.directory` at it:

```bash
./examples/run-with-biome.sh
```

You should see (among other startup lines):

```
Discovered plugin 'biome-generators' v1.0.0 (Daedalus examples) from daedalus-biome-plugin-1.0.0-SNAPSHOT.jar
Biome plugin: registered generators [forest-biome, desert-biome]
Biome plugin: subscribed to MazeGeneratedEvent
Started plugin 'biome-generators' v1.0.0
```

Then in another shell:

```bash
curl -X POST http://localhost:8080/api/v1/maze/generate \
  -H 'Content-Type: application/json' \
  -d '{"generatorId":"forest-biome","rows":20,"cols":20,"seed":42}'
```

and watch the server log emit one `[biome] maze generated ...` line per call.

## Why programmatic listener registration?

The plugin is loaded by `java.util.ServiceLoader`, not by Spring's bean
factory. Spring's `EventListenerMethodProcessor` only scans actual beans, so
a `@EventListener` annotation on a plugin method is silently ignored.
Registering an `ApplicationListener` through Spring's
`ApplicationEventMulticaster` (a well-known bean Spring registers by
default under the name `applicationEventMulticaster`) is the supported
path — see `BiomeGeneratorPlugin#start` for the pattern.

The plugin tracks an `AtomicBoolean armed` flag so it can disarm itself in
`stop()`. Spring's `ApplicationEventMulticaster.removeApplicationListener(...)`
would also work, but it requires the plugin to retain the listener
reference on its own state — the disarm flag is functionally equivalent and
keeps the lifecycle methods one line each.

One subtlety: `MazeGeneratedEvent` extends `PluginEvent`, which is a plain
POJO (not an `ApplicationEvent`). Spring wraps POJO events in
`PayloadApplicationEvent` when publishing, so a raw `ApplicationListener`
receives the wrapper, not the original event. The `@EventListener`
annotation processor unwraps automatically; a programmatic listener has to
do the same. See `BiomeGeneratorPlugin.MazeGeneratedListener` for the
two-line idiom.

### If you copy this for a production plugin

The example types its listener as `ApplicationListener<ApplicationEvent>`,
which means every event Spring fires (context refresh, bean lifecycle,
custom events from other plugins) is delivered and then filtered inside
`onApplicationEvent`. That's fine for a tutorial — the wide net makes it
easy to see proof the plugin is alive — but in a busy production host
the per-event delivery cost adds up. Two tighter alternatives:

- Type the listener as
  `ApplicationListener<PayloadApplicationEvent<MazeGeneratedEvent>>` and
  let Spring's generic-type resolution filter at delivery time. Works in
  Spring 4.2+ via `GenericApplicationListener`'s resolvable-type
  inspection.
- Implement `SmartApplicationListener` with an explicit
  `supportsEventType(ResolvableType)` that returns `true` only for the
  `PayloadApplicationEvent<MazeGeneratedEvent>` shape. Slightly more
  ceremony but the type-filter check is explicit in the source.

Either path means Spring won't even call your listener for unrelated
events. For low-traffic plugins or examples the wide listener is fine.

## Files

| Path | What it is |
|---|---|
| `pom.xml` | Single-module Maven build; `daedalus-plugin-api` + Spring + SLF4J are `provided` (host supplies them at runtime). |
| `src/main/java/.../BiomeGeneratorPlugin.java` | `MazePlugin` implementation — manifest, registration, listener. |
| `src/main/java/.../ForestBiomeGenerator.java` | DFS variant with vertical direction bias. |
| `src/main/java/.../DesertBiomeGenerator.java` | Sidewinder variant with widened runs. |
| `src/main/resources/META-INF/services/com.daedalus.plugin.MazePlugin` | ServiceLoader entry — one line pointing at `BiomeGeneratorPlugin`. |
| `src/test/java/.../BiomeGeneratorsTest.java` | Perfect-maze + seed-determinism + descriptor smoke tests. |
