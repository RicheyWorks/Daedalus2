// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.balance;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.odds.OddsRng;
import java.util.List;
import org.junit.jupiter.api.Test;

class FleetBalanceTest {

    @Test
    void shippedConstantsMatchTheCabinetSources() {
        ReedbeatBalance reed = new ReedbeatBalance();
        assertThat(reed.shipped("easy")).containsExactly(4, 18);
        assertThat(reed.shipped("normal")).containsExactly(8, 8);
        assertThat(reed.shipped("hard")).isNull();
        assertThat(reed.supports("hard")).isFalse();
        assertThatThrownBy(() -> reed.play("hard", new OddsRng(1))).isInstanceOf(IllegalArgumentException.class);
        BeaconSweepBalance sweep = new BeaconSweepBalance();
        assertThat(sweep.shipped("easy")).containsExactly(9, 9, 10);
        assertThat(sweep.shipped("normal")).containsExactly(16, 16, 40);
        assertThat(sweep.shipped("hard")).containsExactly(30, 16, 99);
    }

    @Test
    void sameSeedGivesTheSameResults() {
        List<ModeResult> a = FleetReport.checkAll(9L);
        List<ModeResult> b = FleetReport.checkAll(9L);
        assertThat(a).hasSize(6);
        for (int i = 0; i < a.size(); i++) {
            assertThat(a.get(i).toString()).isEqualTo(b.get(i).toString());
        }
    }

    @Test
    void reedbeatRules() {
        // A perfect tapper (no timing error) hits every note: win with hits x 100.
        for (int t = 0; t < 50; t++) {
            SessionOutcome o = new ReedbeatBalance(0).playConfig(new int[] {8, 8, 36}, OddsRng.forTrial(3, t));
            assertThat(o.won()).isTrue();
            assertThat(o.score()).isEqualTo(800);
        }
        // A wild tapper loses after three misses with fewer hits than notes.
        int losses = 0;
        for (int t = 0; t < 200; t++) {
            SessionOutcome o = new ReedbeatBalance(40).playConfig(new int[] {8, 4, 36}, OddsRng.forTrial(4, t));
            if (!o.won()) {
                losses++;
                assertThat(o.score()).isLessThan(800);
            }
        }
        assertThat(losses).isGreaterThan(190);
        // Wider windows never hurt this player (common random numbers, same seeds).
        ReedbeatBalance reed = new ReedbeatBalance();
        int narrow = 0;
        int wide = 0;
        for (int t = 0; t < 1000; t++) {
            narrow += reed.play(new int[] {8, 8}, OddsRng.forTrial(5, t)).won() ? 1 : 0;
            wide += reed.play(new int[] {8, 16}, OddsRng.forTrial(5, t)).won() ? 1 : 0;
        }
        assertThat(wide).isGreaterThan(narrow);
    }

    @Test
    void beaconSweepPlantsLikeTheSourceAndTheSolverIsSound() {
        for (int t = 0; t < 200; t++) {
            OddsRng rng = OddsRng.forTrial(6, t);
            BeaconSweepBalance.Board b = new BeaconSweepBalance.Board(16, 16, 40);
            int first = 8 * 16 + 8;
            assertThat(b.plant(first, rng)).isTrue();
            int count = 0;
            for (int i = 0; i < 256; i++) {
                if (b.mine[i]) {
                    count++;
                    assertThat(Math.abs(i % 16 - 8) > 1 || Math.abs(i / 16 - 8) > 1).isTrue();
                }
            }
            assertThat(count).isEqualTo(40);
            b.reveal(first);
            assertThat(b.lost).isFalse();
            assertThat(b.openSafe).isGreaterThanOrEqualTo(9);
            // Certain moves never open a mine or flag a safe cell.
            while (!b.won() && b.deduce()) {
                assertThat(b.lost).isFalse();
                for (int i = 0; i < 256; i++) {
                    if (b.flag[i]) {
                        assertThat(b.mine[i]).isTrue();
                    }
                }
            }
        }
        // Mines that do not fit outside the first 3x3 cannot be planted: a loss with score 0.
        SessionOutcome full = new BeaconSweepBalance().play(new int[] {9, 9, 75}, new OddsRng(1));
        assertThat(full.won()).isFalse();
        assertThat(full.score()).isZero();
    }

    @Test
    void publishedFlagsAndSuggestions() {
        List<ModeResult> check = FleetReport.checkAll(FleetReport.SEED);
        assertThat(check.get(2).flags()).containsExactly(BalanceFlag.MISSING_MODE);
        assertThat(check.subList(3, 6)).noneMatch(ModeResult::flagged);
        assertThat(check.get(0).winRate()).isGreaterThan(check.get(1).winRate());
        assertThat(check.get(3).winRate()).isGreaterThan(check.get(4).winRate());
        assertThat(check.get(4).winRate()).isGreaterThan(check.get(5).winRate());

        long start = System.nanoTime();
        List<Suggestion> all = FleetReport.tuneAll(FleetReport.SEED);
        assertThat((System.nanoTime() - start) / 1e9).isLessThan(60.0);
        BalanceCheck bands = new BalanceCheck();
        for (String game : List.of("reedbeat", "beacon_sweep")) {
            List<Suggestion> g = all.stream().filter(s -> s.game().equals(game)).toList();
            assertThat(g).hasSize(3).allMatch(Suggestion::found);
            for (Suggestion s : g) {
                BalanceBand b = bands.bandFor(s.difficulty());
                assertThat(s.confirm().low()).isGreaterThanOrEqualTo(b.floor());
                assertThat(s.confirm().high()).isLessThanOrEqualTo(b.ceiling());
            }
            assertThat(BalanceTuner.monotonic(g.stream().map(Suggestion::confirm).toList())).isTrue();
        }
        assertThat(all.get(0).suggested()).containsExactly(4, 14);
        assertThat(all.get(1).suggested()).containsExactly(8, 10);
        assertThat(all.get(2).suggested()).containsExactly(8, 8);
        assertThat(all.get(3).suggested()).containsExactly(9, 9, 10);
        assertThat(all.get(4).suggested()).containsExactly(16, 16, 40);
    }
}
