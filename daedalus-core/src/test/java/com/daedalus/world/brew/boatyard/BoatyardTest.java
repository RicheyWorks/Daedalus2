// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.boatyard;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.boatyard.Boatyard.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class BoatyardTest {
    /** Brute force: relax every wait n times from all-zero starts (Bellman-style longest path). */
    static int brute(Boatyard y) {
        int n = y.jobs();
        int[] start = new int[n];
        for (int round = 0; round < n; round++) {
            for (int[] w : y.waits()) {
                start[w[1]] = Math.max(start[w[1]], start[w[0]] + y.days(w[0]));
            }
        }
        int end = 0;
        for (int i = 0; i < n; i++) {
            end = Math.max(end, start[i] + y.days(i));
        }
        return end;
    }

    /** Keel 3, then ribs 2 and planks 4 side by side, then caulk 1 after both; mast 5 alone. Launch day 8. */
    static Boatyard yard() {
        return new Boatyard(new int[] {3, 2, 4, 1, 5},
                List.of(new int[] {0, 1}, new int[] {0, 2}, new int[] {1, 3}, new int[] {2, 3}));
    }

    @Test
    void seededYardIsDeterministicAndLoopsRefused() {
        Boatyard a = Boatyard.seeded(5);
        Boatyard b = Boatyard.seeded(5);
        assertEquals(a.jobs(), b.jobs());
        assertEquals(a.launchDay(), b.launchDay());
        assertThrows(IllegalArgumentException.class,
                () -> new Boatyard(new int[] {1, 1}, List.of(new int[] {0, 1}, new int[] {1, 0})));
        assertThrows(IllegalArgumentException.class, () -> new Boatyard(new int[] {0}, List.of()));
    }

    @Test
    void launchDayMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            Boatyard y = Boatyard.seeded(seed);
            assertEquals(brute(y), y.launchDay(), "critical path == brute force, seed " + seed);
        }
    }

    @Test
    void sideBySideIsNotTheSum() {
        Boatyard y = yard();
        assertEquals(8, y.launchDay(), "3 + max(2, 4) + 1, not the 15-day total");
        assertEquals(5, y.finish(4), "the mast runs alongside");
    }

    @Test
    void earlyDayEarnsNoCredit() {
        Boatyard y = yard();
        y.plan("p");
        assertEquals(Outcome.EARLY, y.launch("l1", 6));
        assertEquals(String.format(KeeperYardLines.EARLY, 6), y.talk("t1"));
        assertEquals("launch", y.quest().currentStep().type(), "no credit for an early day");
    }

    @Test
    void guards() {
        Boatyard y = yard();
        assertEquals(Outcome.IGNORED, y.launch(" ", 8));
        assertEquals(Outcome.LATE, y.launch("e1", 15));
        assertEquals(Outcome.DUPLICATE, y.launch("e1", 8));
    }

    @Test
    void questLateThenRightThenKeeper() {
        Boatyard y = yard();
        assertEquals(String.format(KeeperYardLines.GREETING, 5), y.talk("t0"));
        y.plan("p0");
        assertEquals(Outcome.LATE, y.launch("l1", 15));
        assertEquals(String.format(KeeperYardLines.LATE, 15, 8), y.talk("t1"));
        assertEquals(Outcome.RIGHT, y.launch("l2", 8));
        assertEquals(KeeperYardLines.THANKS, y.talk("t2"));
        assertNull(y.quest().currentStep());
        assertEquals(KeeperYardLines.DONE, y.talk("t3"));
    }
}
