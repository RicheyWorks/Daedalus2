// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.relay;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.relay.LighthouseRelay.Outcome;
import org.junit.jupiter.api.Test;

class LighthouseRelayTest {
    /** Brute force over every simple path from lighthouse 0 to the last. */
    static int brute(LighthouseRelay r) {
        int[] best = {-1};
        walk(r, 0, 1, Integer.MAX_VALUE, best);
        return best[0];
    }

    private static void walk(LighthouseRelay r, int at, int seen, int low, int[] best) {
        if (at == r.lamps() - 1) {
            best[0] = Math.max(best[0], low);
            return;
        }
        for (int v = 0; v < r.lamps(); v++) {
            if ((seen >> v & 1) == 0 && r.clarity(at, v) != LighthouseRelay.NONE) {
                walk(r, v, seen | 1 << v, Math.min(low, r.clarity(at, v)), best);
            }
        }
    }

    static void set(int[][] c, int a, int b, int v) {
        c[a][b] = v;
        c[b][a] = v;
    }

    static int[][] coast() {
        int[][] c = new int[4][4];
        set(c, 0, 1, 8);
        set(c, 1, 2, 7);
        set(c, 2, 3, 9);
        set(c, 0, 3, 2);
        return c;
    }

    @Test
    void seededCoastIsDeterministic() {
        LighthouseRelay r = LighthouseRelay.seeded(1);
        assertTrue(r.lamps() >= 4 && r.lamps() <= 7);
        assertEquals(r.clearest(), LighthouseRelay.seeded(1).clearest());
        assertThrows(IllegalArgumentException.class, () -> new LighthouseRelay(new int[][] {{0, 1}, {3, 0}}));
    }

    @Test
    void clearestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            LighthouseRelay r = LighthouseRelay.seeded(seed);
            assertEquals(brute(r), r.clearest(), "widest path == brute force, seed " + seed);
        }
    }

    @Test
    void directSightlineIsNotAlwaysClearest() {
        assertEquals(7, new LighthouseRelay(coast()).clearest());
    }

    @Test
    void noRelayEarnsNoCredit() {
        int[][] c = new int[4][4];
        set(c, 0, 1, 5);
        set(c, 1, 2, 5);
        LighthouseRelay r = new LighthouseRelay(c);
        assertEquals(-1, r.clearest());
        r.light("l1", 1);
        assertEquals(Outcome.NO_RELAY, r.signal("s1"));
        assertEquals(KeeperRelayLines.NO_RELAY, r.talk("t1"));
        assertEquals("signal", r.quest().currentStep().type(), "no credit without a relay");
    }

    @Test
    void guards() {
        LighthouseRelay r = new LighthouseRelay(coast());
        assertEquals(Outcome.IGNORED, r.light("", 1));
        assertEquals(Outcome.NO_SIGHT, r.light("e0", 2));
        assertEquals(Outcome.NOT_THERE, r.light("e0", 7));
        assertEquals(Outcome.NOT_THERE, r.signal("s0"));
        assertEquals(Outcome.LIT, r.light("e1", 1));
        assertEquals(Outcome.DUPLICATE, r.light("e1", 2));
    }

    @Test
    void questDimThenWellThenKeeper() {
        LighthouseRelay r = new LighthouseRelay(coast());
        assertEquals(String.format(KeeperRelayLines.GREETING, 3), r.talk("t0"));
        r.light("a1", 3);
        assertEquals(Outcome.DIM, r.signal("s1"));
        assertEquals(String.format(KeeperRelayLines.DIM, 2, 7), r.talk("t1"));
        assertEquals("signal", r.quest().currentStep().type(), "no credit for a dim relay");
        r.restart();
        r.light("b1", 1);
        assertEquals("Lamp 1 lit, haziest sightline so far 8.", KeeperRelayLines.line(r));
        r.light("b2", 2);
        r.light("b3", 3);
        assertEquals(Outcome.WELL, r.signal("s2"));
        assertEquals(KeeperRelayLines.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperRelayLines.DONE, r.talk("t3"));
    }
}
