// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.OptionalInt;
import java.util.SplittableRandom;
import java.util.function.Supplier;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

import org.junit.jupiter.api.Test;

/**
 * Java = C++ for the ark tree cores (G572 port of G520, G524 and G527). Each engines/unreal/core-test/ark_*_parity.txt
 * is written from this class (run with -Dark.parity.write=true) and replayed line for line by the matching
 * ark_*_core_test.cpp against its DaedalusArk*Core.h header. Inputs come from SplittableRandom(seed), which the C++
 * side draws bit for bit through StableRng.
 */
class ArkTreesParityTest {

    private static final Path CORE_TEST = Path.of("..", "engines", "unreal", "core-test");
    static final int SEEDS = 60;

    static String join(long[] a) {
        return a.length == 0 ? "-" : Arrays.stream(a).mapToObj(Long::toString).collect(Collectors.joining(","));
    }

    static String join(List<Integer> a) {
        return a.isEmpty() ? "-" : a.stream().map(Object::toString).collect(Collectors.joining(","));
    }

    /** Random tree (each spar hangs off an earlier one), strains in [-20, 20], six queries around one re-tension. */
    static List<String> shroudPaths() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= SEEDS; s++) {
            SplittableRandom rng = new SplittableRandom(s);
            int n = 1 + rng.nextInt(12);
            int[][] lines = new int[n - 1][];
            StringBuilder held = new StringBuilder();
            for (int v = 1; v < n; v++) {
                lines[v - 1] = new int[] {rng.nextInt(v), v};
                held.append(v > 1 ? "," : "").append(lines[v - 1][0]).append('-').append(v);
            }
            long[] strain = new long[n];
            for (int v = 0; v < n; v++) {
                strain[v] = rng.nextInt(41) - 20;
            }
            ShroudPaths board = new ShroudPaths(n, lines, strain);
            StringBuilder q = new StringBuilder();
            for (int k = 0; k < 6; k++) {
                if (k == 3) {
                    int v = rng.nextInt(n);
                    long value = rng.nextInt(41) - 20;
                    board.set(v, value);
                    q.append(" set=").append(v).append(':').append(value);
                }
                int a = rng.nextInt(n);
                int b = rng.nextInt(n);
                q.append(" q=").append(a).append('-').append(b).append(':').append(board.pathMax(a, b)).append('/')
                        .append(board.pathSum(a, b)).append('/').append(board.meet(a, b)).append('/')
                        .append(board.pathLength(a, b));
            }
            out.add("seed=" + s + " n=" + n + " lines=" + (held.length() == 0 ? "-" : held) + " strain="
                    + join(strain) + q);
        }
        return out;
    }

    /** Sixteen random adds, removes and clash checks on a ledger seeded with s, then three stabs. */
    static List<String> berthLeases() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= SEEDS; s++) {
            SplittableRandom rng = new SplittableRandom(1000 + s);
            BerthLeases ledger = new BerthLeases(s);
            List<long[]> held = new ArrayList<>();
            StringBuilder ops = new StringBuilder();
            int nextId = 0;
            for (int k = 0; k < 16; k++) {
                int kind = rng.nextInt(4);
                long from = rng.nextInt(30);
                long to = from + rng.nextInt(8);
                if (kind <= 1) {
                    ledger.add(nextId, from, to);
                    held.add(new long[] {nextId, from});
                    ops.append(" add=").append(nextId++).append(':').append(from).append('-').append(to);
                } else if (kind == 2 && !held.isEmpty()) {
                    long[] gone = held.remove(rng.nextInt(held.size()));
                    ops.append(" remove=").append(gone[0]).append(':').append(ledger.remove((int) gone[0], gone[1]));
                } else {
                    OptionalInt c = ledger.clash(from, to);
                    ops.append(" clash=").append(from).append('-').append(to).append(':')
                            .append(c.isPresent() ? Integer.toString(c.getAsInt()) : "-");
                }
            }
            for (int k = 0; k < 3; k++) {
                long x = rng.nextInt(38);
                ops.append(" stab=").append(x).append(':').append(join(ledger.stab(x)));
            }
            out.add("seed=" + s + " size=" + ledger.size() + ops);
        }
        return out;
    }

    /** Random wave heights in [0, 5] (ties on purpose): tree, reigns, windows ruled and five window crests. */
    static List<String> swellCrests() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= SEEDS; s++) {
            SplittableRandom rng = new SplittableRandom(s);
            int n = 1 + rng.nextInt(14);
            long[] heights = new long[n];
            for (int i = 0; i < n; i++) {
                heights[i] = rng.nextInt(6);
            }
            SwellCrests chart = new SwellCrests(heights);
            long[] parents = new long[n];
            long[] reigns = new long[n];
            long[] ruled = new long[n];
            for (int i = 0; i < n; i++) {
                parents[i] = chart.parent(i);
                reigns[i] = chart.reignFrom(i) * 100L + chart.reignTo(i);
                ruled[i] = chart.windowsRuled(i);
            }
            StringBuilder q = new StringBuilder();
            for (int k = 0; k < 5; k++) {
                int a = rng.nextInt(n);
                int b = a + rng.nextInt(n - a);
                q.append(" crest=").append(a).append('-').append(b).append(':').append(chart.crest(a, b));
            }
            out.add("seed=" + s + " heights=" + join(heights) + " root=" + chart.root() + " parents=" + join(parents)
                    + " reigns=" + join(reigns) + " ruled=" + join(ruled) + q);
        }
        return out;
    }

    @Test
    void shroudPathsMatchesCpp() throws IOException {
        check("ark_shroud_paths_parity.txt", "G520 ShroudPaths", ArkTreesParityTest::shroudPaths);
    }

    @Test
    void berthLeasesMatchesCpp() throws IOException {
        check("ark_berth_leases_parity.txt", "G524 BerthLeases", ArkTreesParityTest::berthLeases);
    }

    @Test
    void swellCrestsMatchesCpp() throws IOException {
        check("ark_swell_crests_parity.txt", "G527 SwellCrests", ArkTreesParityTest::swellCrests);
    }

    private static void check(String file, String core, Supplier<List<String>> lines) throws IOException {
        Path path = CORE_TEST.resolve(file);
        List<String> actual = lines.get();
        if (Boolean.getBoolean("ark.parity.write")) {
            List<String> body = new ArrayList<>();
            body.add("# " + core + " parity (G572): written by ArkTreesParityTest.java, replayed by "
                    + file.replace("_parity.txt", "_core_test.cpp") + ". Seeds 1.." + SEEDS + ".");
            body.addAll(actual);
            Files.write(path, body, StandardCharsets.UTF_8);
        }
        List<String> expected = Files.readAllLines(path, StandardCharsets.UTF_8).stream()
                .filter(l -> !l.startsWith("#") && !l.isBlank()).toList();
        assertThat(expected).hasSize(SEEDS);
        IntStream.range(0, SEEDS)
                .forEach(i -> assertThat(actual.get(i)).as("%s line %d", file, i).isEqualTo(expected.get(i)));
    }
}
