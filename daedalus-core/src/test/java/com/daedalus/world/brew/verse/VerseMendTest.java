// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.verse;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.verse.Edit.Kind;
import com.daedalus.world.brew.verse.VerseMend.Outcome;
import org.junit.jupiter.api.Test;

class VerseMendTest {
    /** Plain recursion over swap, add and drop with no table: the oracle. */
    static int brute(String a, String b) {
        if (a.isEmpty()) {
            return b.length();
        }
        if (b.isEmpty()) {
            return a.length();
        }
        int swap = brute(a.substring(1), b.substring(1)) + (a.charAt(0) == b.charAt(0) ? 0 : 1);
        int drop = brute(a.substring(1), b) + 1;
        int add = brute(a, b.substring(1)) + 1;
        return Math.min(swap, Math.min(drop, add));
    }

    @Test
    void seededDriftIsDeterministic() {
        VerseMend v = VerseMend.seeded(4);
        assertEquals(v.sung(), VerseMend.seeded(4).sung());
        assertTrue(v.fewest() <= 3, "at most three drift edits");
        assertThrows(IllegalArgumentException.class, () -> new VerseMend("Salt", "salt"));
    }

    @Test
    void fewestMatchesRecursionAndScriptMends() {
        for (long seed = 0; seed < 30; seed++) {
            VerseMend v = VerseMend.seeded(seed);
            assertTrue(v.sung().length() <= 10 && v.carved().length() <= 7, "recursion stays small");
            assertEquals(brute(v.sung(), v.carved()), v.fewest(), "DP == recursion, seed " + seed);
            String s = v.sung();
            for (Edit e : v.bestScript()) {
                s = e.apply(s);
            }
            assertEquals(v.carved(), s, "walk-back script mends it, seed " + seed);
            assertEquals(v.fewest(), v.bestScript().size());
        }
    }

    @Test
    void oneDropBeatsManySwaps() {
        // "ttide" -> "tide": one letter too many, so a single drop of the doubled t mends it.
        VerseMend v = new VerseMend("tide", "ttide");
        assertEquals(1, v.fewest());
        assertEquals(Kind.DROP, v.bestScript().get(0).kind());
    }

    @Test
    void anEmptyVerseIsAllAdds() {
        VerseMend v = new VerseMend("oar", "");
        assertEquals(3, v.fewest());
        assertTrue(v.bestScript().stream().allMatch(e -> e.kind() == Kind.ADD));
    }

    @Test
    void guards() {
        VerseMend v = new VerseMend("gull", "gul");
        assertEquals(Outcome.IGNORED, v.change("", new Edit(Kind.ADD, 3, 'l')));
        assertEquals(Outcome.BAD_EDIT, v.change("e0", new Edit(Kind.SWAP, 3, 'l')));
        assertEquals(Outcome.BAD_EDIT, v.change("e0", new Edit(Kind.ADD, 1, 'L')));
        assertEquals(Outcome.OFF, v.ring("r0"));
        assertEquals(Outcome.CHANGED, v.change("e1", new Edit(Kind.ADD, 3, 'l')));
        assertEquals(Outcome.DUPLICATE, v.change("e1", new Edit(Kind.DROP, 0, ' ')));
        assertEquals("gull", v.current());
    }

    @Test
    void questRoughThenTrueThenKeeper() {
        VerseMend v = new VerseMend("wren", "wern");
        assertEquals(2, v.fewest());
        assertEquals(String.format(KeeperVerseLines.GREETING, "wern", "wren"), v.talk("t0"));
        v.change("c1", new Edit(Kind.DROP, 1, ' '));
        assertEquals("\"wrn\" now, after 1 changes.", KeeperVerseLines.line(v));
        v.change("c2", new Edit(Kind.DROP, 1, ' '));
        v.change("c3", new Edit(Kind.ADD, 1, 'r'));
        v.change("c4", new Edit(Kind.ADD, 2, 'e'));
        assertEquals(KeeperVerseLines.READY, v.talk("t1"));
        assertEquals(Outcome.ROUGH, v.ring("r1"));
        assertEquals(String.format(KeeperVerseLines.ROUGH, 4, 2), v.talk("t2"));
        assertEquals("ring", v.quest().currentStep().type(), "no credit for a rough verse");
        assertEquals(Outcome.STARTED_OVER, v.startOver("s1"));
        v.change("d1", new Edit(Kind.SWAP, 1, 'r'));
        v.change("d2", new Edit(Kind.SWAP, 2, 'e'));
        assertEquals(Outcome.TRUE, v.ring("r2"));
        assertEquals(KeeperVerseLines.THANKS, v.talk("t3"));
        assertNull(v.quest().currentStep());
        assertEquals(KeeperVerseLines.DONE, v.talk("t4"));
    }
}
