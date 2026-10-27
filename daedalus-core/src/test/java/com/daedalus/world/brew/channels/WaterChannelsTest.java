// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.channels;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.channels.WaterChannels.Outcome;
import org.junit.jupiter.api.Test;

class WaterChannelsTest {
    /** Brute force: the smallest cut over every split of the basins with the spring on one side, cistern on the other. */
    static int brute(WaterChannels w) {
        int n = w.basins();
        int best = Integer.MAX_VALUE;
        for (int mask = 0; mask < (1 << n); mask++) {
            if ((mask & 1) == 0 || (mask & (1 << (n - 1))) != 0) {
                continue;
            }
            int cut = 0;
            for (int a = 0; a < n; a++) {
                for (int b = 0; b < n; b++) {
                    if ((mask & (1 << a)) != 0 && (mask & (1 << b)) == 0) {
                        cut += w.channel(a, b);
                    }
                }
            }
            best = Math.min(best, cut);
        }
        return best;
    }

    /** Spring 0 sends 3 and 2; the channels into the cistern take only 2 and 2, so 4 arrive, not 5. */
    static WaterChannels hill() {
        return new WaterChannels(new int[][] {{0, 3, 2, 0}, {0, 0, 1, 2}, {0, 0, 0, 2}, {0, 0, 0, 0}});
    }

    @Test
    void seededHillIsDeterministic() {
        WaterChannels a = WaterChannels.seeded(8);
        WaterChannels b = WaterChannels.seeded(8);
        assertEquals(a.basins(), b.basins());
        assertEquals(a.most(), b.most());
        assertThrows(IllegalArgumentException.class, () -> new WaterChannels(new int[][] {{0}}));
        assertThrows(IllegalArgumentException.class, () -> new WaterChannels(new int[][] {{0, -1}, {0, 0}}));
    }

    @Test
    void mostMatchesBruteForceCut() {
        for (long seed = 0; seed < 30; seed++) {
            WaterChannels w = WaterChannels.seeded(seed);
            assertEquals(brute(w), w.most(), "Edmonds-Karp == smallest cut, seed " + seed);
        }
    }

    @Test
    void springOutputIsNotTheAnswer() {
        assertEquals(4, hill().most(), "5 leave the spring, 4 reach the cistern");
    }

    @Test
    void overflowEarnsNoCredit() {
        WaterChannels w = hill();
        w.trace("tr");
        assertEquals(Outcome.OVERFLOW, w.open("o1", 5));
        assertEquals(String.format(KeeperChannelLines.OVERFLOW, 5), w.talk("t1"));
        assertEquals("open", w.quest().currentStep().type(), "no credit for an overflow");
    }

    @Test
    void guards() {
        WaterChannels w = hill();
        assertEquals(Outcome.IGNORED, w.open("", 4));
        assertEquals(Outcome.SHORT, w.open("e1", 1));
        assertEquals(Outcome.DUPLICATE, w.open("e1", 4));
    }

    @Test
    void questShortThenRightThenKeeper() {
        WaterChannels w = hill();
        assertEquals(String.format(KeeperChannelLines.GREETING, 4), w.talk("t0"));
        w.trace("tr0");
        assertEquals(Outcome.SHORT, w.open("o1", 3));
        assertEquals(String.format(KeeperChannelLines.SHORT, 3, 4), w.talk("t1"));
        assertEquals(Outcome.RIGHT, w.open("o2", 4));
        assertEquals(KeeperChannelLines.THANKS, w.talk("t2"));
        assertNull(w.quest().currentStep());
        assertEquals(KeeperChannelLines.DONE, w.talk("t3"));
    }
}
