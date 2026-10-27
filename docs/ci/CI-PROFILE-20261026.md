# Daedalus2 CI profile - 26 October 2026

Source: GitHub Actions run history for RicheyWorks/Daedalus2, read-only via `gh`
(no local builds). Collected 26 Oct 2026 ~17:55 PT by 2hot2trot for Codex backlog
item 19 (CI speed and reliability). Durations are run `startedAt`..`updatedAt`
for successful runs. Numbers are measurements, not estimates.

## Workflow `CI` (last 100 runs, 97 completed, 19:27Z-00:48Z 26 Oct)

| metric | value |
|---|---|
| success / failure / cancelled | 86 / 1 / 10 |
| reruns (attempt > 1) | 0 |
| success duration median / p90 / max | 6.6 / 10.3 / 15.7 min |

Cancels are superseded pull_request runs (concurrency group, by design since #300).
No flake signal: zero reruns and one failure in 97 runs.

### Job and step timing (20 most recent successful runs, median / p90)

| job :: step | median | p90 |
|---|---|---|
| Build & test :: JOB | 382 s | 399 s |
| Build & test :: Build & test the reactor (`mvn clean install`) | 309 s | 332 s |
| Build & test :: API sweep | 27 s | 27 s |
| Build & test :: remaining examples | 17 s | 18 s |
| Build & test :: checkout | 8 s | 9 s |
| Build & test :: setup-java (maven cache restore) | 3 s | 5 s |
| Windows plugin host :: JOB | 93 s | 109 s |
| Windows plugin host :: PluginHostShutdownTest (`-pl daedalus-server -am`) | 59 s | 62 s |
| Windows plugin host :: setup-java | 11 s | 22 s |

Coverage badge steps total under 10 s. The Maven cache already hits
(`setup-java` `cache: maven`, "Cache restored successfully"), so dependency
download is not the bottleneck.

### Reactor module times (run 40427998542, total 5:13)

| module | time |
|---|---|
| Core Engine | 2:03 |
| Server (REST + WebSocket) | 2:16 |
| Desktop (JavaFX, depends on server) | 15.6 s |
| Explore (depends on core, plugin-api) | 11.6 s |
| Parent / Plugin API / Wallet / Plugin Runtime | 3.8 / 5.9 / 7.1 / 9.0 s |

Core and Server tests are about 85% of the critical path and run serially
(server depends on core via plugin-runtime).

## Other workflows (last 400 runs across all workflows, ~4 h window)

About 70 workflows exist; most are small path-scoped checks with 2-48 runs in the
window, zero failures and zero reruns. Highest medians: Portal production cores
9.9 min, Photo PDF object policy 9.2 min, World census offline 8.1 min,
Desktop Python game ports 6.8 min (p90 13.9 min, the only workflow with reruns: 2).

## Findings

1. CI is not flaky on current history; nothing to quarantine yet.
2. Dependency caching is already in place and hitting; more `~/.m2` caching
   would not help measurably.
3. The cost is test execution in Core and Server. Options, safest first:
   - a. `mvn -T 1C`: lets Explore, Wallet and Plugin API overlap; saving at most
     about 20-30 s (upper bound from module times above). Low risk.
   - b. Shard Server tests into a parallel job that builds upstream with
     `-DskipTests` and tests only `daedalus-server`; projected critical path
     ~6.4 min to ~4.5-5 min. Needs a JaCoCo merge for the badge and keeps the
     `Build & test` check reporting, so it is a separate reviewed PR.
   - c. Surefire `forkCount`/parallel inside Core: needs a local test run under
     the compute lock to prove test isolation first.
4. Branch protection: the API reports `main` as "Branch not protected" with no
   rulesets, so check names are informal; keep `Build & test` and
   `Windows plugin host` unchanged anyway.
