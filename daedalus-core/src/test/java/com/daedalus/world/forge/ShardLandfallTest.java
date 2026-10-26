// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ArkDrydock.Ark;
import com.daedalus.world.forge.ArkDrydock.Life;
import com.daedalus.world.forge.ArkDrydock.Voyage;
import com.daedalus.world.forge.ShardLandfall.Grade;
import com.daedalus.world.forge.ShardLandfall.Hold;
import com.daedalus.world.forge.ShardLandfall.Landing;
import com.daedalus.world.forge.ShardLandfall.Pasture;
import com.daedalus.world.forge.ShardLandfall.Plan;
import com.daedalus.world.forge.VoidCrossing.Crossing;
import com.daedalus.world.forge.VoidCrossing.Outcome;
import org.junit.jupiter.api.Test;

import java.util.EnumMap;
import java.util.Map;
import java.util.SplittableRandom;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ShardLandfallTest {

    private static final Voyage KENNEL = new Voyage("Kennel Isle", 6);

    private static Map<Life, Integer> prices(int each) {
        Map<Life, Integer> m = new EnumMap<>(Life.class);
        for (Life k : ShardLandfall.PAIRED) {
            m.put(k, each);
        }
        return m;
    }

    private static Hold hold(Map<Life, Integer> aboard, int water, int spares) {
        return new Hold("Glass Reef", aboard, water, spares, true);
    }

    /** Every plan the hold allows, scored, the best kept: the brute-force oracle. */
    private static int bruteBest(Hold h, Pasture p) {
        int[] max = new int[ShardLandfall.PAIRED.size() + 1];
        for (int i = 0; i < max.length; i++) {
            max[i] = ShardLandfall.maxUnits(h, i);
        }
        int[] t = new int[max.length];
        int best = Integer.MIN_VALUE;
        while (true) {
            Map<Life, Integer> pairs = new EnumMap<>(Life.class);
            for (int i = 0; i < ShardLandfall.PAIRED.size(); i++) {
                pairs.put(ShardLandfall.PAIRED.get(i), t[i]);
            }
            best = Math.max(best, ShardLandfall.score(h, p, new Plan(pairs, t[max.length - 1])));
            int i = 0;
            while (i < t.length && t[i] == max[i]) {
                t[i] = 0;
                i++;
            }
            if (i == t.length) {
                return best;
            }
            t[i]++;
        }
    }

    @Test
    void theExactKnapsackMatchesBruteForceOnEverySeededHold() {
        SplittableRandom rng = new SplittableRandom(170L);
        int cases = 0;
        for (long seed = 0; seed < 300; seed++) {
            Map<Life, Integer> aboard = new EnumMap<>(Life.class);
            for (Life k : ShardLandfall.PAIRED) {
                aboard.put(k, rng.nextInt(6));
            }
            aboard.put(Life.VENT_BEES, rng.nextInt(4));
            aboard.put(Life.SEED_CRATE, rng.nextInt(3));
            aboard.put(Life.PET, rng.nextInt(2));
            Hold h = hold(aboard, rng.nextInt(2_000), rng.nextInt(13));
            Pasture p = ShardLandfall.pasture(ArkDrydock.SHARDS.get((int) (seed % ArkDrydock.SHARDS.size())), seed);
            Plan best = ShardLandfall.best(h, p);
            assertThat(ShardLandfall.forage(best)).isLessThanOrEqualTo(p.forageCap());
            assertThat(ShardLandfall.score(h, p, best)).as("seed %d", seed).isEqualTo(bruteBest(h, p));
            Landing l = ShardLandfall.land(h, p, best);
            assertThat(l.grade()).isEqualTo(Grade.THRIVING);
            assertThat(l.scrip()).isEqualTo(l.best());
            cases++;
        }
        assertThat(cases).isEqualTo(300);
    }

    @Test
    void onlyWholePairsFoundAHerdSoABrokenPairCannotLand() {
        Map<Life, Integer> aboard = new EnumMap<>(Life.class);
        aboard.put(Life.ASHGOAT, 1);
        aboard.put(Life.EMBERHEN, 3);
        Hold h = hold(aboard, 0, 0);
        assertThat(ShardLandfall.maxUnits(h, 1)).isZero();
        assertThat(ShardLandfall.maxUnits(h, 0)).isEqualTo(1);
        Pasture p = new Pasture("Glass Reef", 500, prices(20), 4);
        assertThatThrownBy(() -> ShardLandfall.land(h, p, new Plan(Map.of(Life.ASHGOAT, 1), 0)))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("0 ashgoat pairs");
        assertThatThrownBy(() -> ShardLandfall.land(h, p, new Plan(Map.of(Life.EMBERHEN, 2), 0)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Plan(Map.of(Life.VENT_BEES, 1), 0)).isInstanceOf(IllegalArgumentException.class);
        Plan best = ShardLandfall.best(h, p);
        assertThat(best.pairs(Life.ASHGOAT)).isZero();
        assertThat(best.pairs(Life.EMBERHEN)).isEqualTo(1);
        // One emberhen pair ashore (20) + the odd hen (5) and the lone goat (5) sold at a quarter price.
        assertThat(ShardLandfall.land(h, p, best).scrip()).isEqualTo(30);
    }

    @Test
    void aThirstyDayInTheVoidBreaksAPairAndTheQuayIsAllThatIsLeft() {
        Ark a = VoidCrossingTest.ark(90, KENNEL, 0);
        long seed = -1;
        Crossing x = null;
        for (long s = 0; s < 5_000 && seed < 0; s++) {
            Crossing c = VoidCrossing.bosun(a, KENNEL, false, 6, s);
            if (c.outcome() == Outcome.ARRIVED_WITH_LOSSES && c.lost().getOrDefault(Life.ASHGOAT, 0) == 1) {
                seed = s;
                x = c;
            }
        }
        assertThat(seed).isNotNegative();
        Hold h = Hold.of(x);
        assertThat(h.arrived()).isTrue();
        assertThat(h.heads(Life.ASHGOAT)).isEqualTo(1);
        Landing l = ShardLandfall.land(x, seed, ShardLandfall.best(h, ShardLandfall.pasture("Kennel Isle", seed)));
        assertThat(l.plan().pairs(Life.ASHGOAT)).isZero();
        assertThat(l.grade()).isEqualTo(Grade.THRIVING);
    }

    @Test
    void theOvergrazedLineSitsExactlyAtTheForageCap() {
        Map<Life, Integer> aboard = new EnumMap<>(Life.class);
        aboard.put(Life.ASHGOAT, 2);
        aboard.put(Life.VENT_BEES, 1);
        Hold h = hold(aboard, 0, 0);
        Plan plan = new Plan(Map.of(Life.ASHGOAT, 1), 1);
        assertThat(ShardLandfall.forage(plan)).isEqualTo(2 * 80 + 10);
        Landing atCap = ShardLandfall.land(h, new Pasture("Glass Reef", 170, prices(12), 5), plan);
        assertThat(atCap.grade()).isEqualTo(Grade.THRIVING);
        assertThat(atCap.herdScrip()).isEqualTo(17);
        Landing oneOver = ShardLandfall.land(h, new Pasture("Glass Reef", 169, prices(12), 5), plan);
        assertThat(oneOver.grade()).isEqualTo(Grade.OVERGRAZED);
        assertThat(oneOver.herdScrip()).isZero();
        assertThat(oneOver.scrip()).isZero();
        assertThat(oneOver.questStep()).isEqualTo("replan_landing");
        assertThat(oneOver.best()).isEqualTo(12 + 1);
        assertThat(oneOver.line()).isEqualTo("Too many mouths for the pasture. Glass Reef is bare by the second week.");
    }

    @Test
    void theSameSeedReplaysTheSamePastureAndLandingByteForByte() {
        Ark a = VoidCrossingTest.ark(90, KENNEL, 600);
        for (long s = 0; s < 50; s++) {
            Crossing x1 = VoidCrossing.bosun(a, KENNEL, true, 6, s);
            Crossing x2 = VoidCrossing.bosun(a, KENNEL, true, 6, s);
            Pasture p1 = ShardLandfall.pasture("Kennel Isle", s);
            assertThat(ShardLandfall.pasture("Kennel Isle", s)).isEqualTo(p1);
            Plan b1 = ShardLandfall.best(Hold.of(x1), p1);
            assertThat(ShardLandfall.land(x1, s, b1).encode()).isEqualTo(ShardLandfall.land(x2, s, b1).encode());
            assertThat(ShardLandfall.best(Hold.of(x2), p1)).isEqualTo(b1);
        }
        boolean differs = false;
        for (long s = 1; s < 20 && !differs; s++) {
            differs = !ShardLandfall.pasture("Kennel Isle", s).equals(ShardLandfall.pasture("Kennel Isle", 0));
        }
        assertThat(differs).isTrue();
        assertThat(ShardLandfall.pasture("Glass Reef", 7)).isNotEqualTo(ShardLandfall.pasture("Sky Orchard", 7));
    }

    @Test
    void pastureRangesStayInTheirBands() {
        for (long s = 0; s < 500; s++) {
            Pasture p = ShardLandfall.pasture(ArkDrydock.SHARDS.get((int) (s % 6)), s);
            assertThat(p.forageCap()).isBetween(100, 500);
            assertThat(p.forageCap() % 50).isZero();
            assertThat(p.hivePrice()).isBetween(3, 6);
            for (Life k : ShardLandfall.PAIRED) {
                assertThat(p.price(k)).isBetween(4, 20);
                assertThat(p.price(k) - 2 * p.sell(k)).isPositive();
            }
        }
    }

    @Test
    void handCheckedScripSeedsPetsWaterAndSpares() {
        Map<Life, Integer> aboard = new EnumMap<>(Life.class);
        aboard.put(Life.EMBERHEN, 2);
        aboard.put(Life.ASHGOAT, 2);
        aboard.put(Life.VENT_BEES, 1);
        aboard.put(Life.PET, 1);
        aboard.put(Life.SEED_CRATE, 2);
        Hold h = hold(aboard, 450, 3);
        Pasture p = new Pasture("Glass Reef", 100, prices(8), 4);
        Landing none = ShardLandfall.land(h, p, Plan.none());
        // quay: water 4 + spares 3 + hive 1 + 4 heads x 2 = 16; seeds 2 x 5 = 10; pet never sold.
        assertThat(none.quayScrip()).isEqualTo(26);
        assertThat(none.herdScrip()).isZero();
        // Best: goats do not fit (160 > 100); emberhen pair (8, frees 4) + hive (4, frees 1) = +7.
        assertThat(none.best()).isEqualTo(33);
        assertThat(none.grade()).isEqualTo(Grade.SETTLED);
        Plan best = ShardLandfall.best(h, p);
        assertThat(best).isEqualTo(new Plan(Map.of(Life.EMBERHEN, 1), 1));
        Landing l = ShardLandfall.land(h, p, best);
        assertThat(l.encode()).isEqualTo("SLF 1 THRIVING to=Glass_Reef cap=100 forage=20 pairs=emberhen:1,ashgoat:0,forgeox:0,"
                + "lavaboar:0,cinderwool:0 hives=1 herd=12 quay=21 scrip=33 best=33 step=report_tessaly | Every pen on Glass Reef"
                + " is full and grazing easy. Tessaly says no ark ever landed better.");
        Pasture rich = new Pasture("Glass Reef", 500, prices(20), 6);
        assertThat(ShardLandfall.land(h, rich, Plan.none()).grade()).isEqualTo(Grade.THIN);
    }

    @Test
    void aBreachedOrUnlaunchedArkBringsNothingAshore() {
        Ark leaky = VoidCrossingTest.ark(90, KENNEL, -1);
        Crossing x = VoidCrossing.bosun(leaky, KENNEL, false, 0, 1L);
        assertThat(x.outcome()).isEqualTo(Outcome.NOT_LAUNCHED);
        Landing l = ShardLandfall.land(x, 1L, Plan.none());
        assertThat(l.grade()).isEqualTo(Grade.NOTHING_ASHORE);
        assertThat(l.scrip()).isZero();
        assertThat(l.questStep()).isEqualTo("sail_again");
        Hold breached = new Hold("Cinder Shoal", Map.of(Life.ASHGOAT, 2), 900, 4, false);
        assertThat(ShardLandfall.land(breached, ShardLandfall.pasture("Cinder Shoal", 3), Plan.none()).grade())
                .isEqualTo(Grade.NOTHING_ASHORE);
    }

    @Test
    void plansRefuseNegativeOrders() {
        assertThatThrownBy(() -> new Plan(Map.of(Life.ASHGOAT, -1), 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Plan(Map.of(), -1)).isInstanceOf(IllegalArgumentException.class);
        assertThat(new Plan(Map.of(Life.ASHGOAT, 0), 0)).isEqualTo(Plan.none());
    }
}
