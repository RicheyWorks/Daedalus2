// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.lanes;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.lanes.MarketLanes.Dir;
import com.daedalus.world.brew.lanes.MarketLanes.Outcome;
import org.junit.jupiter.api.Test;

class MarketLanesTest {
    /** Brute force over every east/south path from (i, j) to the inn. */
    static int brute(MarketLanes m, int i, int j) {
        int here = m.crowd(i, j);
        if (i == m.rows() - 1 && j == m.cols() - 1) {
            return here;
        }
        int best = Integer.MAX_VALUE;
        if (j + 1 < m.cols()) {
            best = Math.min(best, brute(m, i, j + 1));
        }
        if (i + 1 < m.rows()) {
            best = Math.min(best, brute(m, i + 1, j));
        }
        return here + best;
    }

    /** 1 9 1 / 1 9 1 / 1 1 1: the quiet way is south, south, east, east. */
    static MarketLanes small() {
        return new MarketLanes(new int[][] {{1, 9, 1}, {1, 9, 1}, {1, 1, 1}});
    }

    @Test
    void seededMarketIsDeterministic() {
        MarketLanes m = MarketLanes.seeded(8);
        assertTrue(m.rows() >= 3 && m.rows() <= 6 && m.cols() >= 3 && m.cols() <= 6);
        assertEquals(m.least(), MarketLanes.seeded(8).least());
        assertThrows(IllegalArgumentException.class, () -> new MarketLanes(new int[][] {{1, 2}, {3}}));
    }

    @Test
    void leastMatchesBruteForceAndPathAchievesIt() {
        for (long seed = 0; seed < 30; seed++) {
            MarketLanes m = MarketLanes.seeded(seed);
            assertEquals(brute(m, 0, 0), m.least(), "DP == brute force, seed " + seed);
            for (Dir d : m.bestPath()) {
                m.step("s" + m.passed() + d + m.row() + m.col(), d);
            }
            assertTrue(m.atInn(), "walk-back reaches the inn, seed " + seed);
            assertEquals(m.least(), m.passed(), "walk-back passes the least crowd, seed " + seed);
        }
    }

    @Test
    void theGreedyQuietestNextStepIsNotAlwaysBest() {
        // greedy picks the quieter neighbour each step: 0 -> 1 (east) then into 50s; best goes south through 2s.
        MarketLanes m = new MarketLanes(new int[][] {{0, 1, 50}, {2, 50, 50}, {2, 2, 2}});
        assertEquals(8, m.least());
        assertEquals(Dir.SOUTH, m.bestPath().get(0));
    }

    @Test
    void aOneSquareMarketIsAlreadyThere() {
        MarketLanes m = new MarketLanes(new int[][] {{4}});
        assertTrue(m.atInn());
        assertEquals(Outcome.EASY, m.arrive("a1"));
    }

    @Test
    void guards() {
        MarketLanes m = small();
        assertEquals(Outcome.IGNORED, m.step(null, Dir.EAST));
        assertEquals(Outcome.AT_GATE, m.back("b0"));
        assertEquals(Outcome.NOT_THERE, m.arrive("a0"));
        assertEquals(Outcome.STEPPED, m.step("e1", Dir.EAST));
        assertEquals(Outcome.DUPLICATE, m.step("e1", Dir.EAST));
        assertEquals(Outcome.STEPPED, m.step("e2", Dir.EAST));
        assertEquals(Outcome.BLOCKED, m.step("e3", Dir.EAST));
        assertEquals(Outcome.BACKED, m.back("b1"));
        assertEquals(1, m.col());
    }

    @Test
    void questJostledThenEasyThenKeeper() {
        MarketLanes m = small();
        assertEquals(5, m.least());
        assertEquals(KeeperLaneLines.GREETING, m.talk("t0"));
        m.step("s1", Dir.EAST);
        assertEquals("10 people passed so far.", KeeperLaneLines.line(m));
        m.step("s2", Dir.SOUTH);
        m.step("s3", Dir.SOUTH);
        m.step("s4", Dir.EAST);
        assertEquals(KeeperLaneLines.READY, m.talk("t1"));
        assertEquals(Outcome.JOSTLED, m.arrive("a1"));
        assertEquals(String.format(KeeperLaneLines.JOSTLED, 21, 5), m.talk("t2"));
        assertEquals("arrive", m.quest().currentStep().type(), "no credit for a jostled walk");
        for (int k = 0; k < 4; k++) {
            m.back("b" + k);
        }
        m.step("q1", Dir.SOUTH);
        m.step("q2", Dir.SOUTH);
        m.step("q3", Dir.EAST);
        m.step("q4", Dir.EAST);
        assertEquals(Outcome.EASY, m.arrive("a2"));
        assertEquals(KeeperLaneLines.THANKS, m.talk("t3"));
        assertNull(m.quest().currentStep());
        assertEquals(KeeperLaneLines.DONE, m.talk("t4"));
    }
}
