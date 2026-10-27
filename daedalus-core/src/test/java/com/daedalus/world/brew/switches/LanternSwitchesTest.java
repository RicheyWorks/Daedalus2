// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.switches;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.switches.LanternSwitches.Outcome;
import org.junit.jupiter.api.Test;

class LanternSwitchesTest {
    /** Brute force: breadth-first search over patterns, one flip per step. */
    static int brute(LanternSwitches s) {
        int[] dist = new int[1 << s.width()];
        java.util.Arrays.fill(dist, -1);
        java.util.ArrayDeque<Integer> q = new java.util.ArrayDeque<>();
        dist[s.now()] = 0;
        q.add(s.now());
        while (!q.isEmpty()) {
            int u = q.poll();
            for (int i = 0; i < s.width(); i++) {
                int v = u ^ (1 << i);
                if (dist[v] < 0) {
                    dist[v] = dist[u] + 1;
                    q.add(v);
                }
            }
        }
        return dist[s.want()];
    }

    /** 4 lanterns, 0111 to 1000: 4 flips, though the numbers are 1 apart. */
    static LanternSwitches fixture() {
        return new LanternSwitches(4, 0b0111, 0b1000);
    }

    @Test
    void seededIsDeterministic() {
        assertEquals(LanternSwitches.seeded(1).now(), LanternSwitches.seeded(1).now());
        assertEquals(LanternSwitches.seeded(1).flips(), LanternSwitches.seeded(1).flips());
        assertThrows(IllegalArgumentException.class, () -> new LanternSwitches(0, 0, 0));
        assertThrows(IllegalArgumentException.class, () -> new LanternSwitches(2, 4, 0));
    }

    @Test
    void answerMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            LanternSwitches r = LanternSwitches.seeded(seed);
            assertEquals(brute(r), r.flips(), "fast == brute force, seed " + seed);
            assertEquals(Integer.bitCount(r.now() ^ r.want()), r.flips(), "bitCount agrees, seed " + seed);
        }
    }

    @Test
    void trap() {
        LanternSwitches r = fixture();
        assertEquals(4, r.flips());
        assertEquals(1, r.gap());
        assertEquals(Outcome.WRONG, r.count("c0", 1), "numbers one apart can differ in every lantern");
        assertEquals(String.format(KeeperLanternSwitches.WRONG, 1), r.talk("t0"));
    }

    @Test
    void wrongAndSpecialEarnNoCredit() {
        LanternSwitches r = fixture();
        r.read("r");
        assertEquals(Outcome.WRONG, r.count("c1", 4 + 1));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong answer");
        LanternSwitches sp = new LanternSwitches(3, 5, 5);
        assertTrue(sp.match());
        assertEquals(Outcome.MATCH, sp.count("x", 0));
        assertEquals(KeeperLanternSwitches.MATCH, sp.talk("tx"));
    }

    @Test
    void guards() {
        LanternSwitches r = fixture();
        assertEquals(Outcome.IGNORED, r.count("", 4));
        assertEquals(Outcome.IGNORED, r.count(null, 4));
        assertEquals(Outcome.RIGHT, r.count("e1", 4));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 4));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        LanternSwitches r = fixture();
        assertEquals(String.format(KeeperLanternSwitches.GREETING, "0111", "1000"), r.talk("t0"));
        r.read("r0");
        assertEquals(Outcome.WRONG, r.count("c1", 1));
        assertEquals(Outcome.RIGHT, r.count("c2", 4));
        assertEquals(KeeperLanternSwitches.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperLanternSwitches.DONE, r.talk("t3"));
    }
}
