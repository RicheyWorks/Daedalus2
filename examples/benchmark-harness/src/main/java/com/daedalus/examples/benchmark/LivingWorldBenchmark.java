// SPDX-License-Identifier: MIT
package com.daedalus.examples.benchmark;

import com.daedalus.world.WorldId;
import com.daedalus.world.simulation.LivingWorld;
import com.daedalus.world.simulation.SimulationCodec;
import com.daedalus.world.simulation.SimulationTimeline;
import java.lang.management.ManagementFactory;
import java.util.Arrays;
import java.util.Locale;
import java.util.UUID;

/** Manual benchmark in the existing harness family. Synthetic region updates, not concurrent players. */
public final class LivingWorldBenchmark {
    private LivingWorldBenchmark() { }
    public static void main(String[] args) throws Exception {
        Locale.setDefault(Locale.ROOT);
        int iterations = args.length == 0 ? 100_000 : Integer.parseInt(args[0]);
        if (iterations < 1000 || iterations > 10_000_000) throw new IllegalArgumentException("Iterations must be 1000..10000000");
        System.out.println("# java=" + System.getProperty("java.version") + ",os=" + System.getProperty("os.name")
                + ",processors=" + Runtime.getRuntime().availableProcessors());
        System.out.println("regions,updates,elapsed_ms,updates_per_second,p50_update_ns,p95_update_ns,heap_before_bytes,heap_after_bytes");
        for (int regions : new int[]{1, 100, 1000}) {
            var states = new LivingWorld.State[regions];
            for (int i = 0; i < regions; i++) states[i] = LivingWorld.initial(new WorldId("region-" + i), i);
            for (int i = 0; i < 10_000; i++) update(states, i);
            long memoryBefore = usedHeap();
            long[] samples = new long[1000];
            long begin = System.nanoTime();
            for (int i = 0; i < iterations; i++) {
                if (i < samples.length) {
                    long start = System.nanoTime(); update(states, i); samples[i] = System.nanoTime() - start;
                } else update(states, i);
            }
            long elapsed = System.nanoTime() - begin;
            long memoryAfter = usedHeap();
            Arrays.sort(samples);
            System.out.printf("%d,%d,%.3f,%.3f,%d,%d,%d,%d%n", regions, iterations, elapsed / 1e6,
                    iterations * 1e9 / elapsed, samples[499], samples[949], memoryBefore, memoryAfter);
            if (states[0].tick() == 0) throw new AssertionError("Benchmark did not update state");
        }
        var timeline = SimulationTimeline.start(LivingWorld.initial(WorldId.ZERO, 7));
        for (int i = 1; i <= 64; i++) timeline = timeline.append(LivingWorld.Input.advance(i * 3L)).timeline();
        var stored = new SimulationCodec.Stored(1000, 1000, "benchmark", timeline);
        for (int i = 0; i < 100; i++) SimulationCodec.decode(SimulationCodec.encode(stored));
        long encode = 0; long decode = 0; int bytes = 0;
        for (int i = 0; i < 1000; i++) {
            long begin = System.nanoTime(); byte[] encoded = SimulationCodec.encode(stored); encode += System.nanoTime() - begin;
            begin = System.nanoTime(); var recovered = SimulationCodec.decode(encoded); decode += System.nanoTime() - begin;
            if (!recovered.timeline().state().equals(timeline.state())) throw new AssertionError("Recovery diverged");
            bytes = encoded.length;
        }
        System.out.println("snapshot_bytes,retained_inputs,samples,mean_encode_us,mean_replay_recovery_us");
        System.out.printf("%d,%d,1000,%.3f,%.3f%n", bytes, timeline.entries().size(), encode / 1e6, decode / 1e6);
        fullReceiptBenchmark();
        System.out.println("# heap readings include garbage; no peak/retained-memory or network/player-capacity claim");
    }
    private static void fullReceiptBenchmark() throws Exception {
        var state = LivingWorld.initial(WorldId.ZERO, 7);
        for (int i = 0; i < LivingWorld.MAX_RECEIPTS; i++) {
            state = LivingWorld.apply(state, LivingWorld.Input.advance(state.tick() + 12)).state();
            state = LivingWorld.apply(state, LivingWorld.Input.supply(new UUID(0, i).toString(), "benchmark", 1)).state();
        }
        for (int i = 0; i < 200; i++) state = LivingWorld.apply(state, LivingWorld.Input.advance(state.tick() + 64)).state();
        long begin = System.nanoTime();
        for (int i = 0; i < 1000; i++) state = LivingWorld.apply(state, LivingWorld.Input.advance(state.tick() + 64)).state();
        long elapsed = System.nanoTime() - begin;
        var timeline = SimulationTimeline.start(state);
        for (int i = 0; i < 64; i++) timeline = timeline.append(LivingWorld.Input.advance(timeline.state().tick() + 64)).timeline();
        var stored = new SimulationCodec.Stored(1000, 1000, "benchmark", timeline);
        byte[] encoded = SimulationCodec.encode(stored);
        begin = System.nanoTime();
        for (int i = 0; i < 20; i++) {
            if (!SimulationCodec.decode(encoded).timeline().state().equals(timeline.state())) throw new AssertionError("Recovery diverged");
        }
        long recovery = System.nanoTime() - begin;
        System.out.println("stress_receipts,catchup_ticks,updates,mean_update_us,snapshot_bytes,replay_samples,mean_replay_recovery_us");
        System.out.printf("%d,64,1000,%.3f,%d,20,%.3f%n", state.receipts().size(), elapsed / 1e6,
                encoded.length, recovery / 20e3);
    }
    private static void update(LivingWorld.State[] states, int index) {
        int slot = index % states.length;
        states[slot] = LivingWorld.apply(states[slot], LivingWorld.Input.advance(states[slot].tick() + 1)).state();
    }
    private static long usedHeap() { return ManagementFactory.getMemoryMXBean().getHeapMemoryUsage().getUsed(); }
}
