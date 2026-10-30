// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.ark.ArkCellar.Lot;
import com.daedalus.world.ark.CellarRotation.Policy;
import com.daedalus.world.ark.CellarRotation.Result;
import com.daedalus.world.companion.TonicBottler.Tier;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

import org.junit.jupiter.api.Test;

class CellarRotationTest {

    @Test
    void earliestExpiryMatchesExhaustiveSearch() {
        for (long seed = 1; seed <= 300; seed++) {
            Random rnd = new Random(seed);
            List<Lot> shelf = randomShelf(rnd, 1 + rnd.nextInt(6));
            List<Integer> demand = new ArrayList<>();
            for (int i = 0; i < 1 + rnd.nextInt(5); i++) {
                demand.add(rnd.nextInt(3));
            }
            int start = rnd.nextInt(4);
            Result r = CellarRotation.serve(shelf, start, demand, 1, Policy.EARLIEST_EXPIRY);
            int best = best(shelf, start, demand, 0, 0, new boolean[shelf.size()]);
            assertThat(r.served()).as("seed %d", seed).isEqualTo(best);
            assertThat(r.served() + r.missed())
                    .isEqualTo(demand.stream().mapToInt(Integer::intValue).sum());
        }
    }

    @Test
    void freshestFirstNeverBeatsEarliestExpiryAndSometimesLoses() {
        boolean lost = false;
        for (long seed = 1; seed <= 300; seed++) {
            Random rnd = new Random(seed);
            List<Lot> shelf = randomShelf(rnd, 8);
            List<Integer> demand = List.of(1, 1, 1, 1, 1, 1, 1, 1);
            int edf = CellarRotation.serve(shelf, 0, demand, 1, Policy.EARLIEST_EXPIRY).served();
            int fresh = CellarRotation.serve(shelf, 0, demand, 1, Policy.FRESHEST).served();
            assertThat(edf).isGreaterThanOrEqualTo(fresh);
            lost |= fresh < edf;
        }
        assertThat(lost).isTrue();
    }

    @Test
    void handPickedRotationServesTheOldBottleFirst() {
        List<Lot> shelf = List.of(new Lot(Tier.T1, 0), new Lot(Tier.T4, 0));
        List<Integer> demand = List.of(0, 1, 0, 0, 1);
        Result edf = CellarRotation.serve(shelf, 0, demand, 1, Policy.EARLIEST_EXPIRY);
        assertThat(edf.served()).isEqualTo(2);
        assertThat(edf.wasted()).isZero();
        Result fresh = CellarRotation.serve(shelf, 0, demand, 1, Policy.FRESHEST);
        assertThat(fresh.served()).isEqualTo(1);
        assertThat(fresh.wasted()).isEqualTo(1);
    }

    @Test
    void minLevelAndQuestHook() {
        List<Lot> shelf = List.of(new Lot(Tier.T1, 0), new Lot(Tier.T3, 0));
        assertThat(CellarRotation.serve(shelf, 0, List.of(2), Tier.T3.level(),
                Policy.EARLIEST_EXPIRY).served()).isEqualTo(1);
        assertThat(CellarRotation.quest(shelf, 0, List.of(1, 1), 1)).isTrue();
        assertThat(CellarRotation.quest(shelf, 0, List.of(3), 1)).isFalse();
        assertThat(CellarRotation.QUEST_ID).isEqualTo("q_cellar_rotation");
        assertThatThrownBy(() -> CellarRotation.serve(shelf, 0, List.of(-1), 1, Policy.FRESHEST))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void worksOnARealArkCellarShelf() {
        ArkCellar cellar = new ArkCellar(ArkCellar.Rules.defaults());
        ArkCellar.State s = cellar.start(300);
        for (int d = 0; d < 5; d++) {
            s = cellar.day(s, d, new ArkCellar.Day(false,
                    java.util.Map.of(Tier.values()[d % 4], 2))).state();
        }
        Result r = CellarRotation.serve(s.cellar(), 5, List.of(2, 2, 2, 2), 1,
                Policy.EARLIEST_EXPIRY);
        assertThat(r.served()).isEqualTo(8);
        assertThat(r.remaining()).isEmpty();
    }

    private static List<Lot> randomShelf(Random rnd, int n) {
        List<Lot> shelf = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            shelf.add(new Lot(Tier.values()[rnd.nextInt(4)], -rnd.nextInt(10)));
        }
        return shelf;
    }

    private static int best(List<Lot> shelf, int start, List<Integer> demand, int dayIdx, int unit,
                            boolean[] used) {
        if (dayIdx == demand.size()) {
            return 0;
        }
        if (unit == demand.get(dayIdx)) {
            return best(shelf, start, demand, dayIdx + 1, 0, used);
        }
        int bestVal = best(shelf, start, demand, dayIdx, unit + 1, used);
        for (int i = 0; i < shelf.size(); i++) {
            if (!used[i] && CellarRotation.usable(shelf.get(i), start + dayIdx, 1)) {
                used[i] = true;
                bestVal = Math.max(bestVal, 1 + best(shelf, start, demand, dayIdx, unit + 1, used));
                used[i] = false;
            }
        }
        return bestVal;
    }
}
