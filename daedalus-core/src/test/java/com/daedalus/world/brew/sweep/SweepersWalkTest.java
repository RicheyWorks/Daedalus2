// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.sweep;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.sweep.SweepersWalk.Outcome;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class SweepersWalkTest {
    /** Brute force: try every order of the paths; possible if any order is a joined walk. */
    static boolean brute(SweepersWalk s) {
        return any(s, new ArrayList<>(), new boolean[s.pathCount()]);
    }

    static boolean any(SweepersWalk s, List<Integer> walk, boolean[] used) {
        if (walk.size() == s.pathCount()) {
            return s.isTrail(walk);
        }
        for (int i = 0; i < used.length; i++) {
            if (!used[i]) {
                used[i] = true;
                walk.add(i);
                boolean found = any(s, walk, used);
                walk.remove(walk.size() - 1);
                used[i] = false;
                if (found) {
                    return true;
                }
            }
        }
        return false;
    }

    /** A square 0-1-2-3-0 plus the diagonal 0-2: spots 1 and 3 have two paths; 0 and 2 have three. Start at 0 or 2. */
    static SweepersWalk yard() {
        return new SweepersWalk(4, List.of(new int[] {0, 1}, new int[] {1, 2}, new int[] {2, 3}, new int[] {3, 0},
                new int[] {0, 2}));
    }

    @Test
    void seededYardIsDeterministic() {
        assertEquals(SweepersWalk.seeded(1).possible(), SweepersWalk.seeded(1).possible());
        assertEquals(SweepersWalk.seeded(1).pathCount(), SweepersWalk.seeded(1).pathCount());
        assertThrows(IllegalArgumentException.class, () -> new SweepersWalk(2, List.of()));
        assertThrows(IllegalArgumentException.class, () -> new SweepersWalk(2, List.of(new int[] {1, 1})));
    }

    @Test
    void possibleMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            SweepersWalk s = SweepersWalk.seeded(seed);
            assertEquals(brute(s), s.possible(), "Euler rule == brute force, seed " + seed);
        }
    }

    @Test
    void startingAtAnEvenSpotIsATrap() {
        SweepersWalk s = yard();
        assertEquals(2, s.oddSpots());
        assertEquals(Outcome.BROKEN, s.sweep("s0", List.of(1, 2, 3, 0, 4)), "diagonal out of reach");
        assertEquals(KeeperSweepersWalk.BROKEN, s.talk("t0"));
    }

    @Test
    void brokenMissedAndNoWalkEarnNoCredit() {
        SweepersWalk s = yard();
        s.look("l");
        assertEquals(Outcome.MISSED, s.sweep("s1", List.of(0, 1, 2, 3)));
        assertEquals(KeeperSweepersWalk.MISSED, s.talk("t1"));
        assertEquals(Outcome.MISSED, s.sweep("s2", List.of(0, 1, 2, 3, 3)));
        assertEquals(Outcome.MALFORMED, s.sweep("s3", List.of(0, 1, 2, 3, 9)));
        assertEquals("sweep", s.quest().currentStep().type(), "no credit for a broken or missed walk");
        SweepersWalk star = new SweepersWalk(5, List.of(new int[] {0, 1}, new int[] {0, 2}, new int[] {0, 3},
                new int[] {0, 4}));
        assertFalse(star.possible());
        assertEquals(Outcome.NO_WALK, star.sweep("x", List.of(0, 1, 2, 3)));
        assertEquals(String.format(KeeperSweepersWalk.NO_WALK, 4), star.talk("tx"));
        SweepersWalk apart = new SweepersWalk(4, List.of(new int[] {0, 1}, new int[] {2, 3}));
        assertFalse(apart.possible(), "two loose paths that don't join");
    }

    @Test
    void guards() {
        SweepersWalk s = yard();
        assertEquals(Outcome.IGNORED, s.sweep("", List.of(4, 1, 0, 3, 2)));
        assertEquals(Outcome.IGNORED, s.sweep("e", null));
        assertEquals(Outcome.SWEPT, s.sweep("e1", List.of(4, 1, 0, 3, 2)));
        assertEquals(Outcome.DUPLICATE, s.sweep("e1", List.of(4, 1, 0, 3, 2)));
    }

    @Test
    void questBrokenThenSweptThenKeeper() {
        SweepersWalk s = yard();
        assertEquals(String.format(KeeperSweepersWalk.GREETING, 4, 5), s.talk("t0"));
        s.look("l0");
        assertEquals(Outcome.BROKEN, s.sweep("s1", List.of(1, 2, 3, 0, 4)));
        assertEquals(Outcome.SWEPT, s.sweep("s2", List.of(0, 1, 2, 3, 4)));
        assertEquals(KeeperSweepersWalk.THANKS, s.talk("t2"));
        assertNull(s.quest().currentStep());
        assertEquals(KeeperSweepersWalk.DONE, s.talk("t3"));
    }
}
