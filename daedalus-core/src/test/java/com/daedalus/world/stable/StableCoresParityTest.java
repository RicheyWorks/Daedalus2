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

    static List<String> tackRoomPegs() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= SEEDS; s++) {
            int n = s % 11;
            int[] w = TackRoomPegs.weights(s, n, 10);
            int[] f = TackRoomPegs.feuds(s, n, 25);
            TackRoomPegs.Room b = TackRoomPegs.best(w, f, 10);
            TackRoomPegs.Room g = TackRoomPegs.firstFit(w, f, 10);
            out.add("seed=" + s + " weight=" + join(w) + " feud=" + join(f) + " best=" + b.pegs() + ":" + join(b.pegOf())
                    + " firstfit=" + g.pegs() + ":" + join(g.pegOf()));
        }
        return out;
    }

    static List<String> hayWagonRound() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= SEEDS; s++) {
            HayWagonRound.Yard y = HayWagonRound.yard(s, s % 9, 10, 6);
            HayWagonRound.Round b = HayWagonRound.best(y);
            HayWagonRound.Round g = HayWagonRound.nearest(y);
            out.add("seed=" + s + " x=" + join(y.x()) + " y=" + join(y.y()) + " open=" + join(y.open()) + " close=" + join(y.close())
                    + " best=" + b.finish() + ":" + join(b.order()) + " nearest=" + g.finish() + ":" + join(g.order()));
        }
        return out;
    }

    static List<String> farriersTwoAnvils() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= SEEDS; s++) {
            int n = s % 9;
            int[] t = FarriersTwoAnvils.durations(s, n);
            int[] p = FarriersTwoAnvils.links(s, n, 30);
            FarriersTwoAnvils.Plan b = FarriersTwoAnvils.best(t, p);
            FarriersTwoAnvils.Plan g = FarriersTwoAnvils.listSchedule(t, p);
            out.add("seed=" + s + " time=" + join(t) + " pred=" + join(p) + " best=" + b.makespan() + ":" + join(b.start()) + ":"
                    + join(b.anvil()) + " list=" + g.makespan() + ":" + join(g.start()) + ":" + join(g.anvil()));
        }
        return out;
    }

    static List<String> bridleRackMatching() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= SEEDS; s++) {
            int n = s % 9;
            int[] temper = BridleRackMatching.temperaments(s, n);
            int[] skill = BridleRackMatching.skills(s, temper);
            int[][] time = BridleRackMatching.times(s, n);
            StringBuilder rows = new StringBuilder();
            for (int[] row : time) {
                rows.append(rows.length() == 0 ? "" : "/").append(join(row));
            }
            BridleRackMatching.Pairing b = BridleRackMatching.best(skill, temper, time);
            BridleRackMatching.Pairing g = BridleRackMatching.cheapestFirst(skill, temper, time);
            out.add("seed=" + s + " temper=" + join(temper) + " skill=" + join(skill) + " time=" + (n == 0 ? "-" : rows)
                    + " best=" + b.ready() + ":" + join(b.groomOf()) + " cheapest=" + g.ready() + ":" + join(g.groomOf()));
        }
        return out;
    }

    static List<String> waterTroughFill() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= SEEDS; s++) {
            WaterTroughFill.Pipes net = WaterTroughFill.pipes(s, 2 + s % 8, 5);
            int demand = 1 + s % 6;
            WaterTroughFill.Plan b = WaterTroughFill.best(net, demand);
            WaterTroughFill.Plan g = WaterTroughFill.cheapestPath(net, demand);
            out.add("seed=" + s + " nodes=" + net.nodes() + " from=" + join(net.from()) + " to=" + join(net.to()) + " cap=" + join(net.cap())
                    + " cost=" + join(net.cost()) + " demand=" + demand + " best=" + b.cost() + ":" + join(b.flow()) + " cheapest=" + g.cost()
                    + ":" + join(g.flow()));
        }
        return out;
    }

    static List<String> lanternPosts() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= SEEDS; s++) {
            int n = 1 + s % 12;
            int reach = s % 4;
            int[] parent = LanternPosts.yard(s, n);
            int[] price = LanternPosts.prices(s, n, 9);
            LanternPosts.Plan b = LanternPosts.best(parent, price, reach);
            LanternPosts.Plan g = LanternPosts.busiestFirst(parent, price, reach);
            out.add("seed=" + s + " parent=" + join(parent) + " price=" + join(price) + " reach=" + reach + " best=" + b.cost() + ":"
                    + join(b.lighter()) + " busiest=" + g.cost() + ":" + join(g.lighter()));
        }
        return out;
    }

    static List<String> hayBaleStacking() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= SEEDS; s++) {
            HayBaleStacking.Bales h = HayBaleStacking.bales(s, s % 10);
            HayBaleStacking.Stack b = HayBaleStacking.best(h);
            HayBaleStacking.Stack g = HayBaleStacking.biggestFirst(h);
            out.add("seed=" + s + " a=" + join(h.a()) + " b=" + join(h.b()) + " height=" + join(h.height()) + " weight=" + join(h.weight())
                    + " strength=" + join(h.strength()) + " best=" + b.height() + ":" + join(b.bottomUp()) + " biggest=" + g.height() + ":"
                    + join(g.bottomUp()));
        }
        return out;
    }

    static List<String> tackLedgerIndex() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= SEEDS; s++) {
            int[] f = TackLedgerIndex.frequencies(s, s % 12, 20);
            TackLedgerIndex.Filing b = TackLedgerIndex.best(f);
            TackLedgerIndex.Filing g = TackLedgerIndex.mostAskedRoot(f);
            out.add("seed=" + s + " freq=" + join(f) + " best=" + b.flips() + ":" + join(b.order()) + " mostasked=" + g.flips() + ":"
                    + join(g.order()));
        }
        return out;
    }

    static List<String> stallPlaques() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= SEEDS; s++) {
            int[] len = StallPlaques.names(s, s % 15, 1, 6);
            StallPlaques.Layout b = StallPlaques.best(len, 12);
            StallPlaques.Layout g = StallPlaques.fillEachLine(len, 12);
            out.add("seed=" + s + " len=" + join(len) + " best=" + b.ugliness() + ":" + join(b.breaks()) + " fill=" + g.ugliness() + ":"
                    + join(g.breaks()));
        }
        return out;
    }

    static List<String> barnUpgrades() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= SEEDS; s++) {
            int n = s % 13;
            int[] v = BarnUpgrades.values(s, n, n / 2, 9, 9);
            int[] need = BarnUpgrades.needs(s, n, n / 2, 40);
            BarnUpgrades.Build b = BarnUpgrades.best(v, need);
            BarnUpgrades.Build g = BarnUpgrades.oneAtATime(v, need);
            out.add("seed=" + s + " value=" + join(v) + " need=" + join(need) + " best=" + b.coin() + ":" + b.chosen() + " oneatatime="
                    + g.coin() + ":" + g.chosen());
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

    @Test
    void tackRoomPegsMatchesCpp() throws IOException {
        check("stable_tack_room_pegs_parity.txt", "G530 TackRoomPegs", StableCoresParityTest::tackRoomPegs);
    }

    @Test
    void hayWagonRoundMatchesCpp() throws IOException {
        check("stable_hay_wagon_round_parity.txt", "G532 HayWagonRound", StableCoresParityTest::hayWagonRound);
    }

    @Test
    void farriersTwoAnvilsMatchesCpp() throws IOException {
        check("stable_farriers_two_anvils_parity.txt", "G535 FarriersTwoAnvils", StableCoresParityTest::farriersTwoAnvils);
    }

    @Test
    void bridleRackMatchingMatchesCpp() throws IOException {
        check("stable_bridle_rack_matching_parity.txt", "G537 BridleRackMatching", StableCoresParityTest::bridleRackMatching);
    }

    @Test
    void waterTroughFillMatchesCpp() throws IOException {
        check("stable_water_trough_fill_parity.txt", "G539 WaterTroughFill", StableCoresParityTest::waterTroughFill);
    }

    @Test
    void lanternPostsMatchesCpp() throws IOException {
        check("stable_lantern_posts_parity.txt", "G540 LanternPosts", StableCoresParityTest::lanternPosts);
    }

    @Test
    void hayBaleStackingMatchesCpp() throws IOException {
        check("stable_hay_bale_stacking_parity.txt", "G542 HayBaleStacking", StableCoresParityTest::hayBaleStacking);
    }

    @Test
    void tackLedgerIndexMatchesCpp() throws IOException {
        check("stable_tack_ledger_index_parity.txt", "G545 TackLedgerIndex", StableCoresParityTest::tackLedgerIndex);
    }

    @Test
    void stallPlaquesMatchesCpp() throws IOException {
        check("stable_stall_plaques_parity.txt", "G547 StallPlaques", StableCoresParityTest::stallPlaques);
    }

    @Test
    void barnUpgradesMatchesCpp() throws IOException {
        check("stable_barn_upgrades_parity.txt", "G548 BarnUpgrades", StableCoresParityTest::barnUpgrades);
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
