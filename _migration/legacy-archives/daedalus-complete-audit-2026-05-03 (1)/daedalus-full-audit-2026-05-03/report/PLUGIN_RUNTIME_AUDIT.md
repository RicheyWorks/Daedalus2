# Daedalus Plugin Runtime — Code Audit Report

**Date**: 2026-05-03  
**Auditor**: Grok (xAI)  
**Module**: daedalus-plugin-runtime (Spring-backed plugin host + discovery)

---

## Executive Summary

**Grade: A-** (excellent design, 2 minor issues fixed)

The runtime module is the **missing glue** that makes the beautiful `plugin-api` actually work inside a Spring Boot application. It is well-written, defensively coded, and follows the same high standards as the rest of Daedalus.

### What It Does Perfectly
- **Classloader isolation** for external plugins (each JAR gets its own `URLClassLoader`).
- **Dependency-ordered bootstrapping** via `PluginRegistry.sortedByDependencies()`.
- **Per-plugin error isolation** — one broken plugin cannot crash the entire system.
- **Clean Spring adapter** (`SpringPluginContext`) — the *only* place in the plugin layer that touches Spring.
- **Graceful degradation** — missing plugin directory, bad JARs, failing plugins are all logged and skipped.

---

## Issues Found & Fixed

### 1. Resource Leak: `URLClassLoader` instances never closed

**File**: `PluginManager.java` (lines 71-82, 115-125)

**Root Cause**:
```java
URLClassLoader cl = new URLClassLoader(new URL[]{url}, ...);
ServiceLoader<MazePlugin> sl = ServiceLoader.load(MazePlugin.class, cl);
// cl is never closed
```

Every external plugin JAR left an open `URLClassLoader`. Over time (or on plugin reload / app restart on Windows) this causes:
- File descriptor leaks
- JAR files that cannot be deleted or replaced
- Potential `OutOfMemoryError` in long-running servers with many plugins

**Fix Applied**:
- Added `private final List<URLClassLoader> externalLoaders = new ArrayList<>();`
- Track every created classloader in `loadJar()`
- Close all of them in `shutdownAll()` (after stopping plugins)
- Clear the list afterwards

**Impact**: Now safe for production use with external plugins, hot-reload scenarios, and Windows deployments.

**Patch**: `patches/01-pluginmanager-classloader-leak.patch`

---

### 2. Public test utility left in production API

**File**: `PluginManager.java:142`

**Root Cause**:
```java
/** For tests / scripted loads. */
public boolean exists(File f) { return f.exists() && f.isFile(); }
```

This method was clearly added for unit tests but was accidentally left `public`. It pollutes the public API of `PluginManager` (a core orchestration class) with a trivial file-existence check.

**Fix Applied**:
Changed to package-private (`boolean exists(...)` — no `public` modifier). It remains usable by tests in the same package but is no longer part of the published API.

**Patch**: Same as above (included in the diff).

---

## Other Observations (No Changes Needed)

| Area | Status | Notes |
|------|--------|-------|
| **Dependency Ordering** | Excellent | `sortedByDependencies()` correctly implements a simple topological sort. Cycles are handled gracefully by appending remaining plugins (with a comment explaining the fallback). |
| **Error Handling** | Excellent | Every plugin lifecycle step is wrapped in try/catch. Failures are recorded in `PluginRegistry.Entry` with the exception attached and logged. Other plugins continue. |
| **Logging** | Good | Consistent SLF4J usage. Could add a `PluginEvent` for "plugin failed" if the host wants to surface failures to the UI. |
| **Thread Safety** | Good | `PluginRegistry` uses `ConcurrentHashMap`. `bootAll()` and `shutdownAll()` are expected to be called from a single thread (Spring startup/shutdown). |
| **Classloader Design** | Excellent | Child classloaders with parent delegation means plugins see the core engine + API but are isolated from each other. Perfect for third-party plugins. |
| **Spring Integration** | Perfect | `SpringPluginContext` is a tiny, final, well-documented adapter. The comment "This is the only place... that touches Spring directly" is accurate and valuable. |

---

## How the Pieces Fit Together (Full Plugin Subsystem)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        daedalus-plugin-api                          │
│  (Spring-free SPI)                                                  │
│  • MazePlugin (interface with default methods)                      │
│  • PluginContext (generators, solvers, publish, bean)               │
│  • PluginEvent / MazeGeneratedEvent / MazeSolvedEvent / ...         │
│  • PluginManifest, AbstractPlugin, PluginLifecycle                  │
└─────────────────────────────────────────────────────────────────────┘
                                  ▲
                                  │ implemented by
                                  │
┌─────────────────────────────────────────────────────────────────────┐
│                     daedalus-plugin-runtime                         │
│  • PluginManager (discover + bootAll + shutdownAll)                 │
│  • PluginRegistry (lifecycle tracking + dependency sort)            │
│  • SpringPluginContext (the Spring adapter)                         │
│  • URLClassLoader isolation for external JARs                       │
└─────────────────────────────────────────────────────────────────────┘
                                  ▲
                                  │ hosted by
                                  │
┌─────────────────────────────────────────────────────────────────────┐
│                          daedalus-server                            │
│  • PluginConfig (creates PluginManager + PluginRegistry beans)      │
│  • PluginController (GET /api/plugins)                              │
│  • MazeWebSocketController (forwards events to STOMP)               │
│  • AlgorithmConfig (built-in generators/solvers as beans)           │
└─────────────────────────────────────────────────────────────────────┘
```

**Data Flow**:
1. Spring starts → `PluginConfig.bootPlugins()` (via `@EventListener(ApplicationReadyEvent)`)
2. `PluginManager.discover()` → ServiceLoader (classpath) + JARs in `./plugins/`
3. `PluginManager.bootAll()` → creates `SpringPluginContext` → calls `init` → `registerAlgorithms` → `start` in dependency order
4. Plugins register new generators/solvers → appear in `GET /api/algorithms`
5. Plugins publish events via `ctx.publish(...)` → Spring event bus → `MazeWebSocketController` → STOMP topics
6. On shutdown: `shutdownAll()` → `stop()` on plugins + close classloaders

---

## Final Recommendations

1. **Apply the classloader fix** — critical for any deployment that loads external plugins.
2. **Consider adding** a `PluginEvent` subtype for "PluginFailedEvent" so the UI / monitoring can react to failures.
3. **Optional enhancement**: Expose `loadedCount()` and `describe()` via a small actuator endpoint or Micrometer gauge.
4. **The plugin subsystem is now complete and production-ready.**

---

**End of Plugin Runtime Audit**
