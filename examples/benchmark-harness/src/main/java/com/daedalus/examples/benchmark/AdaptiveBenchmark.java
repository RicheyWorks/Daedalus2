// SPDX-License-Identifier: MIT
package com.daedalus.examples.benchmark;

import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.solver.solvers.BfsSolver;
import com.daedalus.theory.MazeMetrics;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.World;
import com.daedalus.world.WorldId;
import com.daedalus.world.export.WorldMesher;
import com.daedalus.world.simulation.LivingWorld;
import com.daedalus.world.tactics.AdaptiveDirector;
import com.daedalus.world.tactics.SquadDirector;
import com.daedalus.world.tactics.TacticalMemory;
import com.daedalus.world.tactics.TacticalOrders;

import java.lang.management.ManagementFactory;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.function.Supplier;

/** Reproducible descriptive measurements, never CI timing assertions or network-capacity claims. */
public final class AdaptiveBenchmark {
    private static volatile Object sink;
    private static final int WARMUP = 2000;
    private static final int SAMPLES = 1000;
    private AdaptiveBenchmark() { }

    public static void main(String[] args) throws Exception {
        Path out = Path.of(args.length == 0 ? "tactical-benchmark" : args[0]);
        Files.createDirectories(out);
        List<String> csv = new ArrayList<>();
        csv.add("# java=" + System.getProperty("java.version") + "; os=" + System.getProperty("os.name")
                + "; cpus=" + Runtime.getRuntime().availableProcessors() + "; warmup=" + WARMUP + "; samples=" + SAMPLES);
        csv.add("workload,population,p50_us,p95_us,p99_us,allocated_bytes_per_sample");
        for (int population : new int[] {3, 32, 128, 256, 1024}) {
            List<AdaptiveDirector.Frame> frames = new ArrayList<>();
            for (int first = 0; first < population; first += 256) {
                var units = new ArrayList<SquadDirector.Unit>();
                for (int i = first; i < Math.min(population, first + 256); i++) {
                    units.add(new SquadDirector.Unit("u" + i, new TacticalOrders.Vec(i % 16 * 50, i / 16 * 30, 0),
                            i % 9 == 0 ? 20 : 100, 100, true));
                }
                frames.add(new AdaptiveDirector.Frame("pack-" + first, "demo", 1, units,
                        new TacticalOrders.Vec(1000, 0, 500), new TacticalOrders.Vec(0, 0, 0), true,
                        AdaptiveDirector.WeaponStyle.LONG_RANGE));
            }
            var memory = AdaptiveDirector.Memory.initial("raiders", "demo");
            measure(csv, "adaptive_decision", population, () -> frames.stream().map(f -> AdaptiveDirector.decide(memory, f)).toList());
            var specs = frames.stream().map(f -> AdaptiveDirector.decide(memory, f).orders()).toList();
            measure(csv, "dto1_serialization", population, () -> specs.stream().map(TacticalOrders::write).toList());
            measure(csv, "decision_plus_wire", population, () -> frames.stream().map(f -> TacticalOrders.write(AdaptiveDirector.decide(memory, f).orders())).toList());
        }
        for (int size : new int[] {31, 101}) {
            var generator = new RecursiveBacktrackerGenerator();
            measure(csv, "generation", size, () -> generator.generate(size, size, 42, new MazeStats()));
            var maze = generator.generate(size, size, 42, new MazeStats());
            MazeMetrics.placeStartAndGoalAtExtremes(maze);
            measure(csv, "bfs_route", size, () -> new BfsSolver().solve(maze, maze.start(), maze.goal(), new MazeStats()));
        }
        World world = World.zero();
        for (int x = 0; x < 16; x++) for (int z = 0; z < 16; z++) world.place(new BlockCoordinate(x, 0, z), BlockType.STONE);
        measure(csv, "java_world_mesh", 256, () -> WorldMesher.mesh(world));
        var state = LivingWorld.initial(new WorldId("world-zero"), 42);
        measure(csv, "world_catchup_64", 1, () -> LivingWorld.apply(state, LivingWorld.Input.advance(64)));
        var memory = AdaptiveDirector.Memory.initial("raiders", "demo");
        measure(csv, "faction_checkpoint_roundtrip", 1, () -> TacticalMemory.decode(TacticalMemory.encode(memory)));
        Files.write(out.resolve("baseline.csv"), csv);
        demo(out);
        csv.forEach(System.out::println);
    }

    private static void measure(List<String> csv, String workload, int population, Supplier<Object> operation) {
        for (int i = 0; i < WARMUP; i++) sink = operation.get();
        long[] nanos = new long[SAMPLES];
        var bean = ManagementFactory.getThreadMXBean();
        var allocated = bean instanceof com.sun.management.ThreadMXBean t && t.isThreadAllocatedMemorySupported() ? t : null;
        if (allocated != null && !allocated.isThreadAllocatedMemoryEnabled()) allocated.setThreadAllocatedMemoryEnabled(true);
        long before = allocated == null ? -1 : allocated.getThreadAllocatedBytes(Thread.currentThread().threadId());
        for (int i = 0; i < SAMPLES; i++) {
            long start = System.nanoTime();
            sink = operation.get();
            nanos[i] = System.nanoTime() - start;
        }
        long bytes = allocated == null ? -1 : (allocated.getThreadAllocatedBytes(Thread.currentThread().threadId()) - before) / SAMPLES;
        Arrays.sort(nanos);
        csv.add(String.format(Locale.ROOT, "%s,%d,%.3f,%.3f,%.3f,%d", workload, population,
                nanos[SAMPLES / 2] / 1000.0, nanos[(SAMPLES * 95 / 100) - 1] / 1000.0,
                nanos[(SAMPLES * 99 / 100) - 1] / 1000.0, bytes));
    }

    private static void demo(Path out) throws Exception {
        var units = List.of(new SquadDirector.Unit("guard", new TacticalOrders.Vec(0, 0, 0), 100, 100, true),
                new SquadDirector.Unit("scout", new TacticalOrders.Vec(200, 0, 0), 100, 100, true),
                new SquadDirector.Unit("wounded", new TacticalOrders.Vec(300, 0, 0), 20, 100, true));
        var frame = new AdaptiveDirector.Frame("pack-1", "demo", 1, units, new TacticalOrders.Vec(1000, 0, 0),
                new TacticalOrders.Vec(0, 0, 0), true, AdaptiveDirector.WeaponStyle.LONG_RANGE);
        var decision = AdaptiveDirector.decide(AdaptiveDirector.Memory.initial("raiders", "demo"), frame);
        if (!decision.orders().orders().stream().map(TacticalOrders.Order::verb).toList().equals(List.of(
                TacticalOrders.Verb.DEFEND, TacticalOrders.Verb.FLANK, TacticalOrders.Verb.RETREAT))) {
            throw new IllegalStateException("Three-enemy demonstration lost a tactical role");
        }
        Files.writeString(out.resolve("three-npc.dto"), TacticalOrders.write(decision.orders()));
        Files.write(out.resolve("faction.dtm"), TacticalMemory.encode(decision.memory()));
        var restored = TacticalMemory.decode(Files.readAllBytes(out.resolve("faction.dtm")));
        var retry = AdaptiveDirector.decide(restored, frame);
        if (!retry.equals(decision)) throw new IllegalStateException("Restart retry diverged");
        Files.writeString(out.resolve("restart-proof.txt"), "checkpoint reload + identical frame -> identical decision and memory\n" + decision.assessment() + "\n");
    }
}
