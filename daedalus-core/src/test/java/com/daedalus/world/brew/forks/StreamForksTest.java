// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.forks;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.forks.StreamForks.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class StreamForksTest {
    /** Brute force: float a boat down every stream from every pool and count arrivals. */
    static long brute(StreamForks f, int at) {
        if (at == f.pools() - 1) {
            return 1;
        }
        long n = 0;
        for (int[] s : f.streams()) {
            if (s[0] == at) {
                n += brute(f, s[1]);
            }
        }
        return n;
    }

    /** Two forks in a row, each splitting and rejoining: 2 x 2 = 4 routes over 8 streams. */
    static StreamForks hill() {
        return new StreamForks(7, List.of(new int[] {0, 1}, new int[] {0, 2}, new int[] {1, 3}, new int[] {2, 3},
                new int[] {3, 4}, new int[] {3, 5}, new int[] {4, 6}, new int[] {5, 6}));
    }

    @Test
    void seededHillIsDeterministic() {
        StreamForks a = StreamForks.seeded(3);
        StreamForks b = StreamForks.seeded(3);
        assertEquals(a.pools(), b.pools());
        assertEquals(a.routes(), b.routes());
        assertThrows(IllegalArgumentException.class, () -> new StreamForks(3, List.of(new int[] {2, 1})));
        assertEquals(0, new StreamForks(3, List.of(new int[] {0, 1})).routes(), "no stream reaches the sea");
    }

    @Test
    void routesMatchBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            StreamForks f = StreamForks.seeded(seed);
            assertEquals(brute(f, 0), f.routes(), "DP == enumeration, seed " + seed);
        }
    }

    @Test
    void forksMultiply() {
        assertEquals(4, hill().routes(), "2 then 2 ways, not 2 + 2 forks or 8 streams");
    }

    @Test
    void wrongCountEarnsNoCredit() {
        StreamForks f = hill();
        f.follow("f");
        assertEquals(Outcome.WRONG, f.count("c1", 8));
        assertEquals(String.format(KeeperForkLines.WRONG, 8), f.talk("t1"));
        assertEquals("count", f.quest().currentStep().type(), "no credit for a wrong count");
    }

    @Test
    void guards() {
        StreamForks f = hill();
        assertEquals(Outcome.IGNORED, f.count("", 4));
        assertEquals(Outcome.WRONG, f.count("e1", 2));
        assertEquals(Outcome.DUPLICATE, f.count("e1", 4));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        StreamForks f = hill();
        assertEquals(String.format(KeeperForkLines.GREETING, 7), f.talk("t0"));
        f.follow("f0");
        assertEquals(Outcome.WRONG, f.count("c1", 2));
        assertEquals(Outcome.RIGHT, f.count("c2", 4));
        assertEquals(KeeperForkLines.THANKS, f.talk("t2"));
        assertNull(f.quest().currentStep());
        assertEquals(KeeperForkLines.DONE, f.talk("t3"));
    }
}
