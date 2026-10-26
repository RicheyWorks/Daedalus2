// SPDX-License-Identifier: MIT
// Java 21 source launcher; classpath: core/target/classes and server/target/classes.
import com.daedalus.server.service.tactics.FileTacticalCheckpoints;
import com.daedalus.world.tactics.*;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.Locale;
import java.util.concurrent.*;

/** Closed-loop synthetic contention, not HTTP latency or an Unreal frame benchmark. */
class TacticalHostProbe {
    static final int WARMUP = 5, SAMPLES = 30;
    static final ThreadLocal<Long> ENTER = new ThreadLocal<>();
    public static void main(String[] args) throws Exception {
        System.out.println("# java=" + System.getProperty("java.version") + "; os=" + System.getProperty("os.name")
                + "; warmup_per_worker=" + WARMUP + "; samples_per_worker=" + SAMPLES
                + "; units=3; storage=system-temp; workload=closed-loop-independent-sessions");
        System.out.println("workers,samples,throughput_per_s,total_p50_us,total_p95_us,total_p99_us,pre_brain_p95_us,brain_to_return_p95_us");
        for (int workers : new int[] {1, 4, 8}) run(workers);
    }
    static void run(int workers) throws Exception {
        var directory = Files.createTempDirectory("daedalus-host-probe-");
        long[] total = new long[workers * SAMPLES], before = total.clone(), after = total.clone();
        var barrier = new CyclicBarrier(workers);
        try {
            try (var store = new FileTacticalCheckpoints(directory);
                    var pool = Executors.newFixedThreadPool(workers)) {
                var brain = new AdaptiveTacticsBrain(store, roster -> new AdaptiveTacticsBrain.Context(
                        "faction", new TacticalOrders.Vec(0, 0, 0), false, AdaptiveDirector.WeaponStyle.UNKNOWN));
                var host = TacticsHost.withContext((roster, player) -> {
                    ENTER.set(System.nanoTime());
                    return brain.decide(roster, player);
                });
                var futures = new java.util.ArrayList<Future<?>>();
                long[] begins = new long[workers], ends = new long[workers];
                for (int worker = 0; worker < workers; worker++) {
                    final int id = worker;
                    futures.add(pool.submit(() -> {
                        try {
                            for (int tick = 1; tick <= WARMUP + SAMPLES; tick++) {
                                if (tick == WARMUP + 1) {
                                    barrier.await(30, TimeUnit.SECONDS);
                                    begins[id] = System.nanoTime();
                                }
                                String roster = "DTR 1\nsession probe-" + id + " squad squad tick " + tick
                                        + "\nunit a SLIME 100 100 0 0 0 1\nunit b SLIME 100 100 100 0 0 1\nunit c SLIME 100 100 0 100 0 1\n";
                                String events = "DTE 1\ntick " + tick + "\nevent PLAYER player 1000 0 0 100\n";
                                ENTER.remove();
                                long start = System.nanoTime();
                                var decision = host.decide(roster, events);
                                long end = System.nanoTime();
                                if (decision.result() != TacticsHost.Result.APPLY || ENTER.get() == null
                                        || !TacticalOrders.parse(decision.spec()).ok()) throw new IllegalStateException("Invalid receipt");
                                if (tick > WARMUP) {
                                    int index = id * SAMPLES + tick - WARMUP - 1;
                                    total[index] = end - start;
                                    before[index] = ENTER.get() - start;
                                    after[index] = end - ENTER.get();
                                }
                            }
                            ends[id] = System.nanoTime();
                            var key = new AdaptiveTacticsBrain.Key("probe-" + id, "squad", "faction");
                            if (TacticalMemory.decode(store.load(key)).lastTick() != WARMUP + SAMPLES)
                                throw new IllegalStateException("Final checkpoint tick differs");
                        } finally { ENTER.remove(); }
                        return null;
                    }));
                }
                for (var future : futures) future.get(60, TimeUnit.SECONDS);
                double seconds = (Arrays.stream(ends).max().orElseThrow() - Arrays.stream(begins).min().orElseThrow()) / 1e9;
                Arrays.sort(total); Arrays.sort(before); Arrays.sort(after);
                System.out.printf(Locale.ROOT, "%d,%d,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f%n", workers, total.length,
                        total.length / seconds, percentile(total, .50), percentile(total, .95), percentile(total, .99),
                        percentile(before, .95), percentile(after, .95));
            }
        } finally {
            // Only files in this freshly created flat directory, never a supplied directory.
            try (var files = Files.list(directory)) { for (var file : files.toList()) Files.delete(file); }
            Files.delete(directory);
        }
    }
    static double percentile(long[] sorted, double fraction) {
        return sorted[(int) Math.ceil(sorted.length * fraction) - 1] / 1000.0;
    }
}
