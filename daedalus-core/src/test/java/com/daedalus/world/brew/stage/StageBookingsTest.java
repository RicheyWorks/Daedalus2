// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.stage;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.stage.StageBookings.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class StageBookingsTest {
    /** Brute force: every subset of bookings with no overlaps. */
    static int brute(StageBookings s) {
        List<List<Integer>> b = s.bookings();
        int best = 0;
        for (int m = 0; m < 1 << b.size(); m++) {
            boolean ok = true;
            int coins = 0;
            for (int i = 0; i < b.size(); i++) {
                if ((m >> i & 1) == 0) {
                    continue;
                }
                coins += b.get(i).get(2);
                for (int j = i + 1; j < b.size(); j++) {
                    if ((m >> j & 1) == 1 && b.get(i).get(0) < b.get(j).get(1) && b.get(j).get(0) < b.get(i).get(1)) {
                        ok = false;
                    }
                }
            }
            if (ok) {
                best = Math.max(best, coins);
            }
        }
        return best;
    }

    /** [0-2 for 1], [1-5 for 10], [3-6 for 2]: best 10, earliest-finish greedy 3. */
    static StageBookings fixture() {
        return new StageBookings(List.of(List.of(0, 2, 1), List.of(1, 5, 10), List.of(3, 6, 2)));
    }

    @Test
    void seededIsDeterministic() {
        assertEquals(StageBookings.seeded(1).bookings(), StageBookings.seeded(1).bookings());
        assertEquals(StageBookings.seeded(1).best(), StageBookings.seeded(1).best());
        assertThrows(IllegalArgumentException.class, () -> new StageBookings(List.of(List.of(2, 2, 1))));
        assertThrows(IllegalArgumentException.class, () -> new StageBookings(List.of(List.of(0, 1, 0))));
    }

    @Test
    void answerMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            StageBookings r = StageBookings.seeded(seed);
            assertEquals(brute(r), r.best(), "fast == brute force, seed " + seed);
            assertTrue(r.best() >= r.greedy(), "greedy never beats the best, seed " + seed);
        }
    }

    @Test
    void trap() {
        StageBookings r = fixture();
        assertEquals(10, r.best());
        assertEquals(3, r.greedy());
        assertEquals(Outcome.WRONG, r.count("c0", 3), "the most bands is not the most coins");
        assertEquals(String.format(KeeperStageBookings.WRONG, 3), r.talk("t0"));
    }

    @Test
    void wrongAndSpecialEarnNoCredit() {
        StageBookings r = fixture();
        r.read("r");
        assertEquals(Outcome.WRONG, r.count("c1", 10 + 1));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong answer");
        StageBookings sp = new StageBookings(List.of());
        assertTrue(sp.empty());
        assertEquals(Outcome.EMPTY, sp.count("x", 0));
        assertEquals(KeeperStageBookings.EMPTY, sp.talk("tx"));
    }

    @Test
    void guards() {
        StageBookings r = fixture();
        assertEquals(Outcome.IGNORED, r.count("", 10));
        assertEquals(Outcome.IGNORED, r.count(null, 10));
        assertEquals(Outcome.RIGHT, r.count("e1", 10));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 10));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        StageBookings r = fixture();
        assertEquals(String.format(KeeperStageBookings.GREETING, fixture().bookings()), r.talk("t0"));
        r.read("r0");
        assertEquals(Outcome.WRONG, r.count("c1", 3));
        assertEquals(Outcome.RIGHT, r.count("c2", 10));
        assertEquals(KeeperStageBookings.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperStageBookings.DONE, r.talk("t3"));
    }
}
