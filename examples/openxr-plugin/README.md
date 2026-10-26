# Daedalus example plugin — `openxr-plugin`

Headset backend for [`daedalus-explore`](../../daedalus-explore) (ADR-017).
The explore host is valid with **zero** XR JARs. This plugin is how a
headset attaches.

## What it adds

- `OpenXrRuntime` — `XrRuntime` id `openxr`. `present()` is true only when
  `DAEDALUS_OPENXR=1`, so `mvn verify` never opens a session.
- `OpenXrPlugin` — listed by `GET /api/v1/plugins` if the JAR is in the
  host `plugins/` directory.

A later slice can bind LWJGL OpenXR behind this same class. SteamVR and
vendor runtimes are extra JARs, not compile-time deps of `daedalus-explore`.

## Build

Not a reactor child. After `mvn -pl daedalus-explore -am install` from
the repo root:

```bash
mvn -f examples/openxr-plugin/pom.xml clean package
```

Drop `target/daedalus-openxr-plugin-1.2.0-SNAPSHOT.jar` next to the
explore classpath (or into the server `plugins/` directory).
