// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.function.Supplier;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

import org.junit.jupiter.api.Test;

/**
 * Java = C++ for the stable-lane minigame cores (G567 port). Each engines/unreal/core-test/stable_*_parity.txt is
 * written from this class (run with -Dstable.parity.write=true) and replayed line for line by the matching
 * stable_*_core_test.cpp against its DaedalusStable*Core.h header.
 */
class StableCoresParityTest {

    private static final Path CORE_TEST = Path.of("..", "engines", "unreal", "core-test");
    static final int SEEDS = 60;

    static String join(int[] a) {
        return a.length == 0 ? "-" : Arrays.stream(a).mapToObj(Integer::toString).collect(Collectors.joining(","));
    }

    static List<String> trottingRing() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= SEEDS; s++) {
            int n = s % 13;
            int stamina = s % 5;
            int[] calls = TrottingRing.calls(s, n);
            TrottingRing.Round b = TrottingRing.best(calls, stamina);
            TrottingRing.Round e = TrottingRing.eager(calls, stamina);
            out.add("seed=" + s + " stamina=" + stamina + " calls=" + join(calls) + " best=" + b.score() + ":"
                    + join(b.gaits()) + " eager=" + e.score() + ":" + join(e.gaits()) + " rescore="
                    + TrottingRing.score(calls, e.gaits(), stamina));
        }
        return out;
    }

    static List<String> feedLoft() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= SEEDS; s++) {
            List<FeedLoft.Bale> bales = FeedLoft.delivery(s, s % 9, 6);
            int w = s % 15;
            int k = (s * 7) % 15;
            String held = bales.stream().map(x -> x.weight() + "/" + x.bulk() + "/" + x.nourishment())
                    .collect(Collectors.joining(","));
            FeedLoft.Load b = FeedLoft.best(bales, w, k);
            FeedLoft.Load g = FeedLoft.greedy(bales, w, k);
            out.add("seed=" + s + " weight=" + w + " bulk=" + k + " bales=" + (held.isEmpty() ? "-" : held) + " best="
                    + b.nourishment() + ":" + join(b.bales()) + " greedy=" + g.nourishment() + ":" + join(g.bales()));
        }
        return out;
    }

    static List<String> paddockRotation() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= SEEDS; s++) {
            int[][] p = PaddockRotation.paddocks(s, 1 + s % 4);
            int days = s % 9;
            PaddockRotation.Season b = PaddockRotation.best(p[0], p[1], days);
            PaddockRotation.Season g = PaddockRotation.greedy(p[0], p[1], days);
            out.add("seed=" + s + " days=" + days + " cap=" + join(p[0]) + " growth=" + join(p[1]) + " best="
                    + b.grass() + ":" + join(b.plan()) + " greedy=" + g.grass() + ":" + join(g.plan()));
        }
        return out;
    }

    static List<String> shoeingShed() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= SEEDS; s++) {
            int[][] h = ShoeingShed.horses(s, s % 9);
            ShoeingShed.Queue b = ShoeingShed.best(h[0], h[1], h[2]);
            ShoeingShed.Queue g = ShoeingShed.smith(h[0], h[1], h[2]);
            out.add("seed=" + s + " time=" + join(h[0]) + " fret=" + join(h[1]) + " due=" + join(h[2]) + " best="
                    + b.penalty() + ":" + join(b.order()) + " smith=" + g.penalty() + ":" + join(g.order()));
        }
        return out;
    }

    @Test
    void trottingRingMatchesCpp() throws IOException {
        check("stable_trotting_ring_parity.txt", "G506 TrottingRing", StableCoresParityTest::trottingRing);
    }

    @Test
    void feedLoftMatchesCpp() throws IOException {
        check("stable_feed_loft_parity.txt", "G516 FeedLoft", StableCoresParityTest::feedLoft);
    }

    @Test
    void paddockRotationMatchesCpp() throws IOException {
        check("stable_paddock_rotation_parity.txt", "G523 PaddockRotation", StableCoresParityTest::paddockRotation);
    }

    @Test
    void shoeingShedMatchesCpp() throws IOException {
        check("stable_shoeing_shed_parity.txt", "G528 ShoeingShed", StableCoresParityTest::shoeingShed);
    }

    private static void check(String file, String game, Supplier<List<String>> lines) throws IOException {
        Path path = CORE_TEST.resolve(file);
        List<String> actual = lines.get();
        if (Boolean.getBoolean("stable.parity.write")) {
            List<String> body = new ArrayList<>();
            body.add("# " + game + " parity (G567): written by StableCoresParityTest.java, replayed by "
                    + file.replace("_parity.txt", "_core_test.cpp") + ". Seeds 1.." + SEEDS + ".");
            body.addAll(actual);
            Files.write(path, body, StandardCharsets.UTF_8);
        }
        List<String> expected = Files.readAllLines(path, StandardCharsets.UTF_8).stream()
                .filter(l -> !l.startsWith("#") && !l.isBlank()).toList();
        assertThat(expected).hasSize(SEEDS);
        IntStream.range(0, SEEDS).forEach(i -> assertThat(actual.get(i)).as("%s line %d", file, i).isEqualTo(expected.get(i)));
    }
}
