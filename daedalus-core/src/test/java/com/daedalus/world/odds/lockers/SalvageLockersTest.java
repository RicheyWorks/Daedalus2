// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.lockers;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.OddsRng;
import org.junit.jupiter.api.Test;

class SalvageLockersTest {

    private static final LockerOdds WALL = new LockerOdds(4, 2);

    @Test
    void montyHallNumbers() {
        LockerOdds classic = new LockerOdds(3, 1);
        assertThat(classic.stayKeeper()).isCloseTo(1.0 / 3, within(1e-15));
        assertThat(classic.switchKeeper()).isCloseTo(2.0 / 3, within(1e-15));
        assertThat(classic.switchBlind()).isCloseTo(0.5, within(1e-15));
        assertThat(WALL.lockers()).isEqualTo(4);
        assertThat(WALL.opened()).isEqualTo(2);
        assertThat(WALL.othersClosed()).isEqualTo(1);
        assertThat(WALL.switchKeeper()).isCloseTo(0.75, within(1e-15));
        assertThat(WALL.blindKeepsRound()).isCloseTo(0.5, within(1e-15));
        assertThat(WALL.stayBlind()).isCloseTo(WALL.switchBlind(), within(1e-15));
        LockerOdds wide = new LockerOdds(10, 1);
        assertThat(wide.switchKeeper()).isCloseTo(0.1125, within(1e-15)).isGreaterThan(wide.stayKeeper());
        assertThat(new LockerOdds(10, 8).switchKeeper()).isCloseTo(0.9, within(1e-15));
    }

    @Test
    void notBeingToldWeighsTheOpener() {
        assertThat(WALL.keeperPosterior(0.5)).isCloseTo(2.0 / 3, within(1e-15));
        assertThat(WALL.switchUntold(0.5)).isCloseTo(2.0 / 3, within(1e-15));
        assertThat(WALL.stayUntold(0.5)).isCloseTo(1.0 / 3, within(1e-15));
        assertThat(WALL.keeperPosterior(0)).isZero();
        assertThat(WALL.keeperPosterior(1)).isEqualTo(1.0);
        assertThat(WALL.switchUntold(1)).isCloseTo(WALL.switchKeeper(), within(1e-15));
        assertThat(WALL.switchUntold(0)).isCloseTo(WALL.switchBlind(), within(1e-15));
        for (int tenth = 0; tenth <= 10; tenth++) {
            double prior = tenth / 10.0;
            assertThat(WALL.switchUntold(prior)).isGreaterThanOrEqualTo(WALL.stayUntold(prior) - 1e-15);
        }
    }

    @Test
    void formulasMatchFullEnumeration() {
        for (int n = 3; n <= 7; n++) {
            for (int k = 1; k <= n - 2; k++) {
                LockerOdds odds = new LockerOdds(n, k);
                double[] keeper = enumerate(n, k, true);
                double[] blind = enumerate(n, k, false);
                assertThat(keeper[0]).isCloseTo(odds.stayKeeper(), within(1e-12));
                assertThat(keeper[1]).isCloseTo(odds.switchKeeper(), within(1e-12));
                assertThat(keeper[2]).isCloseTo(1.0, within(1e-12));
                assertThat(blind[0]).isCloseTo(odds.stayBlind(), within(1e-12));
                assertThat(blind[1]).isCloseTo(odds.switchBlind(), within(1e-12));
                assertThat(blind[2]).isCloseTo(odds.blindKeepsRound(), within(1e-12));
            }
        }
    }

    @Test
    void seededRoundsAgreeWithTheExactOdds() {
        double[] keeper = LockerRound.simulate(WALL, LockerRound.Opener.KEEPER, true, 2026, 20_000);
        assertThat(keeper[0]).isCloseTo(0.75, within(0.015));
        assertThat(keeper[3]).isZero();
        assertThat(keeper[1]).isLessThanOrEqualTo(keeper[0]);
        assertThat(keeper[2]).isGreaterThanOrEqualTo(keeper[0]);
        double[] blind = LockerRound.simulate(WALL, LockerRound.Opener.DECKHAND, true, 7, 20_000);
        assertThat(blind[0]).isCloseTo(0.5, within(0.02));
        assertThat(blind[3]).isCloseTo(0.5, within(0.02));
        double[] stay = LockerRound.simulate(WALL, LockerRound.Opener.KEEPER, false, 9, 20_000);
        assertThat(stay[0]).isCloseTo(0.25, within(0.015));
        assertThat(LockerRound.simulate(WALL, LockerRound.Opener.KEEPER, true, 2026, 20_000)).containsExactly(keeper);
        LockerRound r = LockerRound.deal(WALL, 0, LockerRound.Opener.KEEPER, new OddsRng(3));
        assertThat(r.isOpen(0)).isFalse();
        assertThat(r.voided()).isFalse();
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> new LockerOdds(2, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new LockerOdds(4, 3)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new LockerOdds(4, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> WALL.keeperPosterior(1.5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LockerRound.deal(WALL, 4, LockerRound.Opener.KEEPER, new OddsRng(1)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LockerRound.simulate(WALL, LockerRound.Opener.KEEPER, true, 1, 0))
                .isInstanceOf(IllegalArgumentException.class);
        LockerQuest q = new LockerQuest(1);
        assertThatThrownBy(() -> q.decide(true)).isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(q::chanceIfSwitch).isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(q::opener).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void questRunsFiveRounds() {
        LockerQuest q = new LockerQuest(42);
        assertThat(q.keeperLine()).contains("Round 1 of 5");
        int done = 0;
        int enough = 0;
        for (long s = 0; s < 400; s++) {
            LockerQuest t = new LockerQuest(s);
            while (t.stage() == LockerQuest.Stage.READY || t.stage() == LockerQuest.Stage.OFFER) {
                if (t.stage() == LockerQuest.Stage.READY) {
                    if (!t.deal()) {
                        assertThat(t.last()).isEqualTo(LockerRound.Outcome.VOID);
                    }
                    continue;
                }
                if (t.told()) {
                    LockerRound.Opener who = t.opener();
                    double sw = who == LockerRound.Opener.KEEPER ? 0.75 : 0.5;
                    assertThat(t.chanceIfSwitch()).isCloseTo(sw, within(1e-12));
                    assertThat(t.keeperLine()).contains(who == LockerRound.Opener.KEEPER ? "I opened" : "deckhand");
                } else {
                    assertThat(t.chanceIfSwitch()).isCloseTo(2.0 / 3, within(1e-12));
                    assertThat(t.chanceIfStay()).isCloseTo(1.0 / 3, within(1e-12));
                    assertThat(t.keeperLine()).contains("Stay: 33%. Switch: 67%.");
                    assertThatThrownBy(t::opener).isInstanceOf(IllegalStateException.class);
                }
                t.decide(true);
            }
            done++;
            assertThat(t.round()).isEqualTo(LockerQuest.ROUNDS);
            assertThat(t.found() + t.voids()).isLessThanOrEqualTo(LockerQuest.ROUNDS);
            if (t.stage() == LockerQuest.Stage.FOUND_ENOUGH) {
                enough++;
                assertThat(t.found()).isGreaterThanOrEqualTo(LockerQuest.GOAL);
                assertThat(t.keeperLine()).contains("can steer");
            } else {
                assertThat(t.keeperLine()).contains("Not enough");
            }
            assertThatThrownBy(t::deal).isInstanceOf(IllegalStateException.class);
        }
        assertThat(done).isEqualTo(400);
        assertThat(enough).isBetween(160, 240);
    }

    /** Exact {stay, switch, keptRound} by enumerating prize, opened sets and switch targets (pick = locker 0). */
    private static double[] enumerate(int n, int k, boolean keeper) {
        double stay = 0;
        double sw = 0;
        double kept = 0;
        for (int prize = 0; prize < n; prize++) {
            int[] pool = new int[n];
            int size = 0;
            for (int i = 1; i < n; i++) {
                if (!(keeper && i == prize)) {
                    pool[size++] = i;
                }
            }
            int sets = 0;
            double setStay = 0;
            double setSwitch = 0;
            double setKept = 0;
            for (int mask = 0; mask < (1 << size); mask++) {
                if (Integer.bitCount(mask) != k) {
                    continue;
                }
                sets++;
                boolean[] open = new boolean[n];
                boolean shown = false;
                for (int b = 0; b < size; b++) {
                    if ((mask & (1 << b)) != 0) {
                        open[pool[b]] = true;
                        shown |= pool[b] == prize;
                    }
                }
                if (shown) {
                    continue;
                }
                setKept += 1;
                setStay += prize == 0 ? 1 : 0;
                int closed = 0;
                int hit = 0;
                for (int i = 1; i < n; i++) {
                    if (!open[i]) {
                        closed++;
                        hit += i == prize ? 1 : 0;
                    }
                }
                setSwitch += hit / (double) closed;
            }
            stay += setStay / sets / n;
            sw += setSwitch / sets / n;
            kept += setKept / sets / n;
        }
        return new double[] {stay / kept, sw / kept, kept};
    }
}
