// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.refrain;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.refrain.RefrainCount.Outcome;
import org.junit.jupiter.api.Test;

class RefrainCountTest {
    /** Brute force: try the refrain at every place in the song. */
    static int brute(RefrainCount r) {
        int c = 0;
        for (int i = 0; i + r.refrain().length() <= r.song().length(); i++) {
            if (r.song().startsWith(r.refrain(), i)) {
                c++;
            }
        }
        return c;
    }

    /** Song abababab, refrain aba: it starts 3 times (at 0, 2, 4), but only 2 copies fit without overlapping. */
    static RefrainCount song() {
        return new RefrainCount("abababab", "aba");
    }

    @Test
    void seededSongIsDeterministic() {
        assertEquals(RefrainCount.seeded(1).song(), RefrainCount.seeded(1).song());
        assertEquals(RefrainCount.seeded(1).times(), RefrainCount.seeded(1).times());
        assertThrows(IllegalArgumentException.class, () -> new RefrainCount("abd", "a"));
        assertThrows(IllegalArgumentException.class, () -> new RefrainCount("ab", ""));
        assertArrayEquals(new int[] {0, 1, 0, 0, 3, 1, 0}, RefrainCount.zFunction("aabcaab"));
    }

    @Test
    void timesMatchBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            RefrainCount r = RefrainCount.seeded(seed);
            assertEquals(brute(r), r.times(), "Z-function == brute force, seed " + seed);
        }
    }

    @Test
    void skippingOverlapsIsATrap() {
        RefrainCount r = song();
        assertEquals(3, r.times());
        assertEquals(Outcome.WRONG, r.count("c0", 2), "2 skips the overlapping refrains");
        assertEquals(String.format(KeeperRefrain.WRONG, 2), r.talk("t0"));
    }

    @Test
    void wrongAndNeverSungEarnNoCredit() {
        RefrainCount r = song();
        r.hear("h");
        assertEquals(Outcome.WRONG, r.count("c1", 4));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong count");
        RefrainCount never = new RefrainCount("ababab", "bb");
        assertEquals(0, never.times());
        assertEquals(Outcome.NEVER_SUNG, never.count("x", 0));
        assertEquals(KeeperRefrain.NEVER_SUNG, never.talk("tx"));
    }

    @Test
    void guards() {
        RefrainCount r = song();
        assertEquals(Outcome.IGNORED, r.count("", 3));
        assertEquals(Outcome.IGNORED, r.count(null, 3));
        assertEquals(Outcome.RIGHT, r.count("e1", 3));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 3));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        RefrainCount r = song();
        assertEquals(String.format(KeeperRefrain.GREETING, "abababab", "aba"), r.talk("t0"));
        r.hear("h0");
        assertEquals(Outcome.WRONG, r.count("c1", 2));
        assertEquals(Outcome.RIGHT, r.count("c2", 3));
        assertEquals(KeeperRefrain.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperRefrain.DONE, r.talk("t3"));
    }
}
