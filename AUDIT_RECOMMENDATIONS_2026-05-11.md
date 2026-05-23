# Daedalus — Audit of the 2026-05-11 Changes

**Scope**: every file added or modified on 2026-05-11 — the reference biome
plugin (`examples/biome-plugin/`), the two GitHub Actions workflows
(`.github/workflows/`), the core refactor (`LightningGenerator`,
`RecursiveBacktrackerGenerator`, `GrowingTreePolicies.newestWithNormJump`),
the new policy tests, and the documentation churn that came with it
(`README.md`, `BACKLOG.md`, `CHANGELOG.md`, example `README.md`).
**Reviewer**: self-audit, immediately after the work landed.
**Build verified**: no — neither Maven nor Java 21 was available in the
review sandbox. Findings below are static-analysis only. A pre-merge
`mvn -B clean install` followed by `mvn -B -f examples/biome-plugin/pom.xml
clean package` is mandatory to close this audit.

---

## TL;DR

The 2026-05-11 batch shipped working code and tests but contained **three
blockers** (one will break CI on the first run; one ships a badge that
404s; one is a doc-versus-code mismatch about seed stability) and a
handful of warts that misstate what the code does. Total: 3 blockers,
4 warts, 8 nits. Every blocker has a one-line fix. The warts are mostly
documentation telling stories the code doesn't back up.

The strongest single finding: the refactor of `RecursiveBacktrackerGenerator`
**did not change its seed mapping**, despite three documents (class Javadoc,
CHANGELOG, BACKLOG note that motivated the refactor) claiming it did. The
old hand-rolled Fisher–Yates and the engine's `Collections.shuffle` consume
identical random bits for the size-4 `Direction.values()` array; the
starting cell uses the same `nextInt(rows)` / `nextInt(cols)` pair; the
`Direction` enum order is unchanged. RB seeds pinned before 2026-05-11
will resolve to the same maze after 2026-05-11. This is a strictly better
outcome than we shipped — we just have to update the docs.

---

## Blockers

### B1. CI uses `mvn verify`, not `install` — the example-plugin step will fail

**Where**: `.github/workflows/ci.yml`, line 56.

```yaml
- name: Build & test the reactor
  run: mvn -B -ntp clean verify

- name: Build the reference biome-plugin
  # Runs after the reactor so daedalus-plugin-api is in ~/.m2. Tests in
  # the example pom run via the default surefire binding.
  run: mvn -B -ntp -f examples/biome-plugin/pom.xml clean package
```

The comment claims the reactor step puts `daedalus-plugin-api` in
`~/.m2`. It does not — the Maven lifecycle goes
`validate → compile → test → package → verify → install → deploy`, and
`verify` stops before `install`. The example pom resolves
`com.daedalus:daedalus-plugin-api:1.0.0-SNAPSHOT` from `~/.m2` (or a
remote repo); without `install`, the SNAPSHOT isn't there and the
`package` step fails with `Could not resolve dependencies`.

**Fix (one word)**: change `clean verify` to `clean install`. Total
runtime cost is negligible (install just copies built artifacts into
`~/.m2`).

### B2. CI badge points to the wrong GitHub username

**Where**: `README.md`, line 3.

```markdown
[![CI](https://github.com/730richey730/Daedalus2/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/730richey730/Daedalus2/actions/workflows/ci.yml)
```

The actual repository, per `_setup_github.ps1`, lives at
`github.com/richmond423/Daedalus2`. `730richey730` is the email prefix —
it was guessed during README authorship and not verified.

**Fix**: change `730richey730` to `richmond423` in both the badge image
URL and the link target.

### B3. RB seed-mapping claim contradicts the code

**Where**: `RecursiveBacktrackerGenerator.java` Javadoc (lines 22–29) and
`CHANGELOG.md` (lines 114–125). Both assert a seed-mapping change for id
`"recursive-backtracker"`. The pre-refactor RB in
`_migration/legacy-archives/.../RecursiveBacktrackerGenerator.java` (v1.3
archive) lets us prove the negative:

| Step | Pre-refactor RB | Post-refactor RB (via engine) |
|---|---|---|
| Start cell | `rng.nextInt(rows)`, `rng.nextInt(cols)` | `rng.nextInt(rows)`, `rng.nextInt(cols)` |
| Policy pick | n/a (`stack.peek()`) | `newest()` returns `size-1`, consumes 0 bits |
| Direction shuffle | manual Fisher–Yates: `nextInt(4)`, `nextInt(3)`, `nextInt(2)` | `Collections.shuffle` on size-4 List: same three calls |
| Iteration order | shuffled `Direction[]` in order | shuffled `List<Direction>` in order |

`Collections.shuffle(List, Random)` on a size-4 list goes through the
`size < SHUFFLE_THRESHOLD` fast path (`SHUFFLE_THRESHOLD = 5`), which is
the same from-the-top Fisher–Yates as the manual loop. The
`Direction` enum order — `NORTH, SOUTH, EAST, WEST` — is unchanged.
Therefore the random-bit consumption per outer iteration is identical,
and the starting cell is identical. **Same seed produces the same
maze, bit-for-bit.**

The BACKLOG note that motivated the refactor wrote *"the engine's
slow-path neighbour enumeration consumes Random differently from RB's
current Fisher–Yates shuffle"* — that was an unverified worry, and it's
wrong: both are size-4 Fisher–Yates over `Direction.values()`.

**Fix**: rewrite the seed-mapping paragraphs in `RecursiveBacktrackerGenerator`
and `CHANGELOG.md` to state seed compatibility. Optionally add a unit
test that pins a few `(seed, dims) → carved-edges` snapshots to lock the
mapping going forward.

**Why this matters**: any downstream that pinned RB seeds (reproducibility
fixtures, dashboards, regression goldens) is fine. We over-promised
breakage; the actual outcome is strictly better than we documented.

---

## Warts

### W1. `ForestBiomeGenerator`'s "vertical bias" doesn't exist

**Where**: `examples/biome-plugin/.../ForestBiomeGenerator.java` lines
25–31 (Javadoc) and `shuffleWithVerticalBias` lines 100–113.

The implementation:

```java
private static final Direction[] PRIORITY = { NORTH, SOUTH, EAST, WEST };

private static Direction[] shuffleWithVerticalBias(Random rng) {
    Direction[] out = PRIORITY.clone();
    for (int i = out.length - 1; i > 0; i--) {       // Fisher–Yates
        int j = rng.nextInt(i + 1);
        Direction tmp = out[i]; out[i] = out[j]; out[j] = tmp;
    }
    return out;
}
```

This is a fair Fisher–Yates shuffle. By the algorithm's correctness, it
produces every one of the 24 permutations of `{N, S, E, W}` with equal
probability — the starting order has no effect on the output
distribution. The "vertical bias" claim in the Javadoc, descriptor,
example README, and CHANGELOG is therefore false. The generator behaves
exactly like a uniformly-random recursive backtracker.

**Fix options**:

- **Make the claim true.** Replace the uniform Fisher–Yates with a
  weighted first-slot selection (e.g., place N or S in slot 0 with
  probability 0.7, otherwise E or W; Fisher–Yates the remaining three).
  This produces an actual vertical bias.
- **Make the doc true.** Remove the bias claim from Javadoc, descriptor,
  example README, and CHANGELOG; describe the generator honestly as "a
  recursive backtracker, reimplemented from scratch as a worked example".

Either fix closes the gap. The first is more in keeping with the
example's pedagogical purpose ("here's how to write a textured
generator").

### W2. `stop()` rationale invokes a Spring limitation that doesn't exist

**Where**: `BiomeGeneratorPlugin.java` lines 36–39 (Javadoc),
example `README.md` line 77, `CHANGELOG.md` line 53.

All three say *"Spring doesn't expose a portable removal API across
versions"* as the reason for using an `AtomicBoolean armed` disarm
flag rather than removing the listener on stop. Spring's
`ApplicationEventMulticaster` interface has had
`removeApplicationListener(ApplicationListener<?>)` since Spring 3.0
(2009). It's portable. The disarm pattern is still a fine design choice
— it's simpler, doesn't require storing the listener reference on the
plugin instance, and is robust to multicaster swaps — but for a different
reason than we claimed.

**Fix**: rewrite the rationale. Suggested wording:

> Spring's `ApplicationEventMulticaster` does expose
> `removeApplicationListener(...)`, but storing the listener reference on
> the plugin just to remove it later is more state for the same effect.
> The disarm flag is functionally equivalent and reads cleaner.

### W3. Release workflow's CHANGELOG extractor always picks `[Unreleased]` first

**Where**: `.github/workflows/release.yml` lines 76–84.

```awk
/^## \[/ {
    if (in_section) exit
    if ($0 ~ "## \\[" ver "\\]" || $0 ~ /^## \[Unreleased\]/) {
        in_section = 1; print; next
    }
}
in_section { print }
```

The two conditions are checked at every `## [` heading. As soon as
either matches, the script enters the print section. Since
`[Unreleased]` entries live at the top of the file (Keep-A-Changelog
convention) and the file is walked top-to-bottom, the
`[Unreleased]` match always fires first — even when a versioned section
like `## [1.0.0]` exists further down. Tagging `v1.0.0` will extract the
latest `[Unreleased]` section, not the `[1.0.0]` section.

**Fix**: separate the version match from the fallback. Two-pass approach
(easier to read than awk gymnastics): first pass to detect whether the
versioned section exists, second pass to extract. Or rework the single
awk so a versioned match overrides any prior `[Unreleased]` match.
Sample sketch:

```bash
if grep -qE "^## \\[$VERSION\\]" CHANGELOG.md; then
  awk -v ver="$VERSION" '/^## \[/ {if(in_section)exit; if($0 ~ "## \\["ver"\\]"){in_section=1;print;next}} in_section{print}' CHANGELOG.md > release-notes.md
else
  awk '/^## \[/ {if(in_section)exit; if($0 ~ /^## \[Unreleased\]/){in_section=1;print;next}} in_section{print}' CHANGELOG.md > release-notes.md
fi
```

### W4. `run-with-biome.sh` forwards args space-separated, but Spring Boot expects comma-separated

**Where**: `examples/run-with-biome.sh` lines 58–61.

```bash
RUN_ARGS=""
if [[ $# -gt 0 ]]; then
  RUN_ARGS="-Dspring-boot.run.arguments=$(printf '%s ' "$@" | sed 's/ $//')"
fi
```

The `spring-boot-maven-plugin`'s `arguments` parameter is a
comma-separated list, not a space-separated one. A multi-arg invocation
like `./run-with-biome.sh --server.port=8090 --foo=bar` would currently
produce `-Dspring-boot.run.arguments=--server.port=8090 --foo=bar`,
which Spring Boot treats as a single argument literal `--server.port=8090
--foo=bar` (not two args). The single-arg case still works correctly,
which is why the script wasn't caught at write time.

**Fix**: switch the separator.

```bash
RUN_ARGS="-Dspring-boot.run.arguments=$(printf '%s,' "$@" | sed 's/,$//')"
```

---

## Nits

### N1. `BACKLOG.md` missing blank line before `## Stretch goals`

Line 56 ends with `rotation)` and line 57 starts with `## Stretch goals`.
CommonMark requires a blank line before a header. Renders correctly in
some viewers, breaks in strict ones. Fix: add a blank line.

### N2. `BACKLOG.md` "Last consolidated" date stale

Line 13 says `Last consolidated: 2026-05-07`. We removed entries on
2026-05-11 (the closed "Refactoring (core)" section and the closed
"Reference plugin" item under "New surfaces"). Bump to 2026-05-11.

### N3. `LightningGenerator` descriptor uses fragile `(int)` cast on `SPIKE_PROBABILITY * 100`

Line 49: `(int) (SPIKE_PROBABILITY * 100)`. For `0.15`, this evaluates
to `15` (IEEE 754 gives `15.000000000000002`, truncated by `(int)` to
15). For `0.99` it'd evaluate to `98` (since `0.99 * 100` is
`98.99999999999999`). Not a bug today; a trap if someone tunes the
probability. Replace with `Math.round(SPIKE_PROBABILITY * 100)`.

### N4. `pom.xml` comment references the wrong Spring type

`examples/biome-plugin/pom.xml` lines 57–62 comment says *"We need
ConfigurableApplicationContext to register an ApplicationListener
programmatically..."*. The actual code uses
`ApplicationEventMulticaster`. Comment is stale from the earlier
(buggy) draft. Update the wording.

### N5. `MazeGeneratedListener` typed too wide (`ApplicationListener<ApplicationEvent>`)

`BiomeGeneratorPlugin.java` line 130. Receives every event Spring
fires — context refresh, bean lifecycle, etc. — and filters in
`onApplicationEvent`. A more precise type would let Spring filter at
delivery time. For an example plugin this is acceptable and arguably
clearer to a reader; for a production plugin one would type as
`ApplicationListener<PayloadApplicationEvent<MazeGeneratedEvent>>`
or implement `SmartApplicationListener`. Worth noting in the example's
README "if you copy this for a real plugin..." paragraph.

### N6. `isSeedDeterministic` test would pass for a degenerate constant impl

`GrowingTreePoliciesTest.newestWithNormJump_isSeedDeterministic` asserts
two same-seed RNGs agree and that each pick is in range. A buggy
`newestWithNormJump(0.25)` that always returned `0` would still pass
both assertions. Either rename to `picksAreInRangeAndStableUnderSameSeed`
(more honest) or add a value check — e.g., that across 50 trials we see
at least two distinct return values.

### N7. CHANGELOG repeats W1 and W2

The same false claims about ForestBiome's vertical bias and the Spring
listener-removal API appear in the 2026-05-11 CHANGELOG entry. Fixing
W1 / W2 means fixing the CHANGELOG too — not just the Javadoc.

### N8. `BiomeGeneratorPlugin.start` comment is slightly off

The comment block at lines 95–97 says *"We don't filter by source —
every MazeGeneratedEvent flows through, so operators can see proof the
plugin is alive even when the host is generating a non-biome maze."*
This is confusing because we DO filter by event type (only
`MazeGeneratedEvent` logs). "Filter by source" presumably means the
event's `getSource()` field, but that's not obvious. Rephrase to "We
don't filter by which generator fired the event...".

---

## What is correct that the audit verified

- The plugin entry point (`BiomeGeneratorPlugin`) implements
  `MazePlugin` correctly, registers via `META-INF/services/`, and the
  `ApplicationEventMulticaster` lookup is the right Spring path for
  programmatic listener registration. The `PayloadApplicationEvent`
  unwrap is correct given `PluginEvent` is a POJO.
- `DesertBiomeGenerator` is sound: its Sidewinder variant preserves
  the spanning-tree contract (every cell processed exactly once, one
  east-carve or north-riser per non-terminal cell, top-row run forms a
  single corridor as expected). The `1/3 close → average run length 3`
  math is correct.
- `BiomeGeneratorsTest` correctly verifies the perfect-maze invariant
  (BFS-derived edge count = `rows*cols − 1`) and seed determinism (per-cell
  `openNeighbors` comparison).
- `GrowingTreePolicies.newestWithNormJump`'s endpoint short-circuit
  preserves the underlying policies' random-consumption pattern at
  `pJump = 0.0` and `pJump = 1.0`. The endpoint tests in
  `GrowingTreePoliciesTest` correctly distinguish the short-circuit from
  a non-short-circuit implementation (they assert post-loop `rng.nextInt()`
  agreement, which a non-short-circuit version would break).
- `newestWithNormJump_takesBothBranches_underReasonableSampleCount` is
  statistically robust: at `pJump = 0.5`, the probability of missing
  either branch over 200 trials is `2⁻²⁰⁰`, far beyond any plausible
  flakiness threshold.
- The Lightning policy choice is correct in its own right: Lightning's
  seed mapping DID change because it switched from `quadraticNorm()` to
  `newestWithNormJump(0.15)`, which consumes one extra `nextDouble()`
  per call. Unlike RB (B3), this seed-change claim is accurate.
- Both CI workflows parse as valid YAML and run a sensible pipeline
  modulo B1. `setup-java@v4` with `cache: maven` is the modern path.
  The concurrency group cancels in-flight runs correctly. The release
  workflow's `softprops/action-gh-release@v2` upload action is widely
  used and version-pinned to a major.
- The 5-module reactor's main code is unchanged by this audit's scope;
  every change is additive (the example plugin, the two workflows, the
  new policy method) or in-place rewrite of files already covered by
  `PerfectMazePropertyTest` (Lightning + RB). The property test asserts
  invariants only, so it absorbs the policy changes cleanly.

---

## Action items, ordered

| # | Severity | Action |
|---|---|---|
| 1 | Blocker | Change `clean verify` → `clean install` in `.github/workflows/ci.yml` |
| 2 | Blocker | Fix the GitHub username in the README CI badge (`730richey730` → `richmond423`) |
| 3 | Blocker | Verify RB seed compatibility (pinned-output unit test or empirical diff), then rewrite the seed-mapping paragraphs in `RecursiveBacktrackerGenerator` Javadoc + CHANGELOG to state compatibility |
| 4 | Wart | Either implement an actual vertical bias in `ForestBiomeGenerator` or remove the bias claim from code/docs |
| 5 | Wart | Rewrite the `stop()` / disarm-flag rationale in 3 files (plugin Javadoc, example README, CHANGELOG) to drop the false Spring claim |
| 6 | Wart | Rework the release workflow's CHANGELOG extractor to prefer versioned matches over `[Unreleased]` |
| 7 | Wart | Switch `run-with-biome.sh` argument forwarding from space-separated to comma-separated |
| 8 | Nit | Add blank line before `## Stretch goals` in BACKLOG |
| 9 | Nit | Update BACKLOG `Last consolidated` to 2026-05-11 |
| 10 | Nit | `Math.round` instead of `(int)` cast in `LightningGenerator` descriptor |
| 11 | Nit | Update stale comment in `examples/biome-plugin/pom.xml` |
| 12 | Nit | Mention listener-typing trade-off in example README's "if you copy this..." note (or just rename `MazeGeneratedListener` typing for production fidelity) |
| 13 | Nit | Strengthen `isSeedDeterministic` test or rename to match what it actually asserts |
| 14 | Nit | Verify all three claims (vertical bias, Spring removal API, RB seed change) are fixed everywhere they appear in CHANGELOG too |
| 15 | Nit | Rephrase the `start()` "filter by source" comment to "filter by which generator fired the event" |

The audit is closed when items 1–7 are fixed and a clean `mvn install`
+ `mvn -f examples/biome-plugin/pom.xml package` runs green. Items 8–15
are housekeeping that can ship in the same commit or a follow-up.
