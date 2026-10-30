// SPDX-License-Identifier: MIT
// Java 21 source launcher; classpath needs daedalus-core/target/classes and daedalus-server/target/classes.
import com.daedalus.server.service.tactics.FileTacticalCheckpoints;
import com.daedalus.world.tactics.AdaptiveDirector;
import com.daedalus.world.tactics.AdaptiveTacticsBrain;
import com.daedalus.world.tactics.TacticalMemory;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.Locale;

/** Descriptive local-disk timing, not a CI threshold or Unreal frame measurement. */
class TacticalStoreProbe {
    public static void main(String[] args) throws Exception {
        var directory = Files.createTempDirectory("daedalus-tactical-probe-");
        var key = new AdaptiveTacticsBrain.Key("probe", "squad", "faction");
        long[] nanos = new long[100];
        try {
            try (var store = new FileTacticalCheckpoints(directory)) {
                for (int i = 0; i < 120; i++) {
                    byte[] bytes = TacticalMemory.encode(new AdaptiveDirector.Memory("faction", "probe", i, 0, 0, "0".repeat(64)));
                    long start = System.nanoTime();
                    store.save(key, bytes);
                    byte[] restored = store.load(key);
                    long elapsed = System.nanoTime() - start;
                    if (!Arrays.equals(bytes, restored)) throw new IllegalStateException("Checkpoint differs");
                    if (i >= 20) nanos[i - 20] = elapsed;
                }
            }
            Arrays.sort(nanos);
            System.out.println("# java=" + System.getProperty("java.version") + "; os=" + System.getProperty("os.name")
                    + "; warmup=20; samples=100; location=system-temp; includes=forced-save+atomic-replace+load+validation");
            System.out.println("workload,p50_us,p95_us,p99_us");
            System.out.printf(Locale.ROOT, "tactical_checkpoint,%.3f,%.3f,%.3f%n", nanos[50] / 1000.0,
                    nanos[94] / 1000.0, nanos[98] / 1000.0);
        } finally {
            // Only the flat, freshly created probe directory is removed, never a caller-supplied path.
            try (var files = Files.list(directory)) {
                for (var file : files.toList()) Files.delete(file);
            }
            Files.delete(directory);
        }
    }
}
