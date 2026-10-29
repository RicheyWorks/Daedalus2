// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.ringdance;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.ringdance.RingDance.Outcome;
import org.junit.jupiter.api.Test;

class RingDanceTest {
    /** Brute force: every perfect pairing of mixed crowns; count those with no two ribbons crossing. */
    static long brute(RingDance r) {
        return pairings(r.crowns(), new int[r.dancers()], 0);
    }

    static long pairings(String c, int[] partner, int depth) {
        int n = c.length();
        int i = 0;
        while (i < n && partner[i] != 0) {
            i++;
        }
        if (i == n) {
            for (int a = 0; a < n; a++) {
                for (int b = 0; b < n; b++) {
                    int pa = partner[a] - 1;
                    int pb = partner[b] - 1;
                    if (a < b && b < pa && pa < pb) {
                        return 0;
                    }
                }
            }
            return 1;
        }
        long total = 0;
        for (int k = i + 1; k < n; k++) {
            if (partner[k] == 0 && c.charAt(i) != c.charAt(k)) {
                partner[i] = k + 1;
                partner[k] = i + 1;
                total += pairings(c, partner, depth + 1);
                partner[i] = 0;
                partner[k] = 0;
            }
        }
        return total;
    }

    /** SSFSFF: six dancers pair 5 ways ignoring crowns (Catalan 3), but only 2 ways join shell to feather. */
    static RingDance ring() {
        return new RingDance("SSFSFF");
    }

    @Test
    void seededRingIsDeterministic() {
        assertEquals(RingDance.seeded(1).crowns(), RingDance.seeded(1).crowns());
        assertEquals(RingDance.seeded(1).ways(), RingDance.seeded(1).ways());
        assertThrows(IllegalArgumentException.class, () -> new RingDance("SFS"));
        assertThrows(IllegalArgumentException.class, () -> new RingDance("SX"));
    }

    @Test
    void waysMatchBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            RingDance r = RingDance.seeded(seed);
            assertEquals(brute(r), r.ways(), "Catalan DP == brute force, seed " + seed);
        }
    }

    @Test
    void plainCatalanIsATrap() {
        RingDance r = ring();
        assertEquals(2, r.ways());
        assertEquals(5, new RingDance("SFSFSF").ways(), "alternating crowns allow all 5");
        assertEquals(Outcome.WRONG, r.count("c0", 5), "5 ignores the crowns");
        assertEquals(String.format(KeeperRingDance.WRONG, 5), r.talk("t0"));
    }

    @Test
    void wrongAndNoWayEarnNoCredit() {
        RingDance r = ring();
        r.form("f");
        assertEquals(Outcome.WRONG, r.count("c1", 1));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong count");
        RingDance none = new RingDance("SSSSFF");
        assertEquals(0, none.ways());
        assertEquals(Outcome.NO_WAY, none.count("x", 0));
        assertEquals(KeeperRingDance.NO_WAY, none.talk("tx"));
    }

    @Test
    void guards() {
        RingDance r = ring();
        assertEquals(Outcome.IGNORED, r.count("", 2));
        assertEquals(Outcome.IGNORED, r.count(null, 2));
        assertEquals(Outcome.RIGHT, r.count("e1", 2));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 2));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        RingDance r = ring();
        assertEquals(String.format(KeeperRingDance.GREETING, 6, "SSFSFF"), r.talk("t0"));
        r.form("f0");
        assertEquals(Outcome.WRONG, r.count("c1", 5));
        assertEquals(Outcome.RIGHT, r.count("c2", 2));
        assertEquals(KeeperRingDance.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperRingDance.DONE, r.talk("t3"));
    }
}
