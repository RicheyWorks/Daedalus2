# Daedalus multi-module migration

Two-phase migration. Phase 1 happens in your IDE (safest path for package
refactors with import updates). Phase 2 is a mechanical directory restructure.

## Phase 0 — Backup

```cmd
git add .
git commit -m "Pre-multi-module-split snapshot"
```

If the project isn't in git yet, zip the entire `Daedalus` folder.

## Phase 1 — IDE package refactors

In IntelliJ (or your IDE of choice), use **Refactor → Move Class** (F6 in IntelliJ)
to move these five files to new packages. The IDE will update the package
declaration *and* every importing file across the project automatically. Doing
this by hand is error-prone — let the IDE do it.

| File                       | Old package           | New package                  |
| -------------------------- | --------------------- | ---------------------------- |
| `DaedalusApp.java`         | `com.daedalus`        | `com.daedalus.server`        |
| `DaedalusLauncher.java`    | `com.daedalus`        | `com.daedalus.desktop`       |
| `DaedalusPrimaryStage.java`| `com.daedalus`        | `com.daedalus.desktop`       |
| `PluginManager.java`       | `com.daedalus.plugin` | `com.daedalus.server.plugin` |
| `PluginRegistry.java`      | `com.daedalus.plugin` | `com.daedalus.server.plugin` |

When IntelliJ asks "do you want to update X usages?", say yes to all.

After all five moves, the file tree under `src/main/java/com/daedalus/` should
look like:

```
com/daedalus/
├── config/
├── controller/
├── desktop/                     (DaedalusLauncher, DaedalusPrimaryStage)
├── engine/
├── model/
├── plugin/                      (SPI types only — Manager and Registry have moved)
│   └── events/
├── server/                      (DaedalusApp)
│   └── plugin/                  (PluginManager, PluginRegistry)
├── service/
├── solver/
└── ui/
```

Note: there are no `.java` files directly in `com/daedalus/` anymore — they all
live in subpackages.

**Verify Phase 1**: still in single-module mode, run:

```cmd
mvn clean compile
```

It should still compile cleanly. If it doesn't, fix any remaining stale imports
before continuing. Don't move on until the build is green.

## Phase 2 — Directory restructure

From the project root:

```cmd
migrate.bat
```

This script:
1. Creates the four module skeletons (`daedalus-core/`, `daedalus-plugin-api/`,
   `daedalus-server/`, `daedalus-desktop/`) with `src/main/java`,
   `src/main/resources`, and `src/test/java` subtrees.
2. Moves each top-level package from `src/main/java/com/daedalus/` into the
   appropriate module's `src/main/java/com/daedalus/`.
3. Cleans up the now-empty `src/` tree at the root.
4. Removes the stale `target/` directory.

After it completes, no source files live at the old root paths.

## Phase 3 — Drop in poms and resources

The repo now needs five poms and the server resources. From this download:

| Source                                                        | Destination                                              |
| ------------------------------------------------------------- | -------------------------------------------------------- |
| `pom.xml`                                                     | `pom.xml` (overwrite the old one)                        |
| `daedalus-core/pom.xml`                                        | `daedalus-core/pom.xml`                                  |
| `daedalus-plugin-api/pom.xml`                                  | `daedalus-plugin-api/pom.xml`                            |
| `daedalus-server/pom.xml`                                      | `daedalus-server/pom.xml`                                |
| `daedalus-desktop/pom.xml`                                     | `daedalus-desktop/pom.xml`                               |
| `daedalus-server/src/main/resources/application.yml`           | same path                                                |
| `daedalus-server/src/main/resources/application-dev.yml`       | same path                                                |
| `daedalus-server/src/main/resources/application-prod.yml`      | same path                                                |
| `daedalus-server/src/main/resources/application-test.yml`      | same path                                                |
| `daedalus-server/src/main/resources/logback-spring.xml`        | same path                                                |
| `daedalus-server/src/main/resources/banner.txt`                | same path                                                |

## Phase 4 — Build

From the project root:

```cmd
mvn clean install
```

The reactor builds `daedalus-core` first, then `daedalus-plugin-api`, then
`daedalus-server`, then `daedalus-desktop`. Each module's `target/classes/` will
contain only the classes it owns.

To run the desktop app in dev mode:

```cmd
mvn -pl daedalus-desktop -am javafx:run
```

To run the server headless (no desktop):

```cmd
mvn -pl daedalus-server -am spring-boot:run
```

To produce a fat JAR of the desktop app:

```cmd
mvn -pl daedalus-desktop -am package
```

## Common gotchas

**"Package does not exist"** after Phase 2 — usually means a Phase 1 refactor
was missed. Most often it's a stale import of `com.daedalus.DaedalusApp` or
`com.daedalus.plugin.PluginManager` somewhere. Search globally for those
strings; the IDE missed at most one or two.

**`com.daedalus-core` won't compile because it imports something Spring** — the
boundary is doing its job. Either the import is unnecessary (remove it) or that
class belongs in `daedalus-server`, not `daedalus-core`.

**Resources not found at runtime** — the embedded Spring Boot picks up resources
from the *running module's* classpath. If `application.yml` is in
`daedalus-server/src/main/resources/`, both `mvn -pl daedalus-server
spring-boot:run` and `mvn -pl daedalus-desktop javafx:run` will see it (because
desktop depends on server).

**`@Component`/`@Service` not picked up** — Spring's component scan defaults to
the package containing your `@SpringBootApplication`. With `DaedalusApp` now in
`com.daedalus.server`, scanning starts there and traverses subpackages. But
classes in `com.daedalus.config`, `com.daedalus.controller`, `com.daedalus.service`
sit alongside, *not under*, `com.daedalus.server`. Add an explicit
`@SpringBootApplication(scanBasePackages = "com.daedalus")` (or
`@ComponentScan("com.daedalus")` next to `@SpringBootApplication`) to widen the
scan back to the whole `com.daedalus` namespace.

**Lombok in IntelliJ** — if Lombok-generated methods stop resolving after the
restructure, go to *Settings → Build → Compiler → Annotation Processors* and
make sure annotation processing is enabled for each module.

## Follow-up refactors (recommended, not blocking)

These can happen any time after the multi-module split is green:

- **Extract DTOs from controller inner classes.** Move
  `MazeController$GenerateRequest`, `$GenerateResponse`, `$MoveRequest`,
  `$SessionResponse`, `$SolveResponse`, `MazeWebSocketController$*Frame`,
  `PluginController$PluginInfo` into `com.daedalus.api.dto` as Java records.
- **Add API versioning.** Put `@RequestMapping("/api/v1/...")` on every
  controller class. Free now, painful later.
- **Domain purity audit.** Check every class in `com.daedalus.model.*` for
  `@RedisHash`, `@Entity`, `@JsonProperty`, `@JsonInclude`. Anything found
  should move to a parallel persistence/DTO type in `daedalus-server`, with
  MapStruct (or hand-written) mappers translating to/from the pure domain type.
