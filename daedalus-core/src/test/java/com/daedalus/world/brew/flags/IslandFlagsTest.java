// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.flags;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.flags.IslandFlags.Outcome;
import org.junit.jupiter.api.Test;

class IslandFlagsTest {
    /** Brute force: the smallest k for which some assignment of k colours to every isle has no clash. */
    static int brute(IslandFlags f) {
        int n = f.isles();
        for (int k = 1; k <= n; k++) {
            if (tryColour(f, new int[n], 0, k)) {
                return k;
            }
        }
        return n;
    }

    private static boolean tryColour(IslandFlags f, int[] c, int i, int k) {
        if (i == c.length) {
            for (int a = 0; a < c.length; a++) {
                for (int b = a + 1; b < c.length; b++) {
                    if (f.shore(a, b) && c[a] == c[b]) {
                        return false;
                    }
                }
            }
            return true;
        }
        for (int x = 0; x < k; x++) {
            c[i] = x;
            if (tryColour(f, c, i + 1, k)) {
                return true;
            }
        }
        return false;
    }

    static boolean[][] ring(int n) {
        boolean[][] s = new boolean[n][n];
        for (int i = 0; i < n; i++) {
            int j = (i + 1) % n;
            s[i][j] = true;
            s[j][i] = true;
        }
        return s;
    }

    @Test
    void seededMapIsDeterministic() {
        IslandFlags f = IslandFlags.seeded(6);
        assertTrue(f.isles() >= 4 && f.isles() <= 8);
        assertEquals(f.fewest(), IslandFlags.seeded(6).fewest());
        assertThrows(IllegalArgumentException.class, () -> new IslandFlags(new boolean[][] {{true}}));
    }

    @Test
    void fewestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            IslandFlags f = IslandFlags.seeded(seed);
            assertEquals(brute(f), f.fewest(), "subset DP == brute force, seed " + seed);
        }
    }

    @Test
    void oddRingNeedsThree() {
        assertEquals(3, new IslandFlags(ring(5)).fewest());
        assertEquals(2, new IslandFlags(ring(4)).fewest());
        assertEquals(1, new IslandFlags(new boolean[3][3]).fewest(), "no shores, one colour");
    }

    @Test
    void clashEarnsNoCredit() {
        IslandFlags f = new IslandFlags(ring(4));
        for (int i = 0; i < 4; i++) {
            f.dye("d" + i, i, 0);
        }
        assertEquals(Outcome.CLASH, f.raise("r1"));
        assertArrayEquals(new int[] {0, 1}, f.clash());
        assertEquals(String.format(KeeperFlagLines.CLASH, 0, 1), f.talk("t1"));
        assertEquals("raise", f.quest().currentStep().type(), "no credit for a clash");
    }

    @Test
    void guards() {
        IslandFlags f = new IslandFlags(ring(4));
        assertEquals(Outcome.IGNORED, f.dye("", 0, 0));
        assertEquals(Outcome.NOT_THERE, f.dye("e0", 4, 0));
        assertEquals(Outcome.BAD_COLOUR, f.dye("e0", 0, 4));
        assertEquals(Outcome.UNFINISHED, f.raise("r0"));
        assertEquals(Outcome.DYED, f.dye("e1", 0, 1));
        assertEquals(Outcome.DUPLICATE, f.dye("e1", 1, 1));
    }

    @Test
    void questWastefulThenWellThenKeeper() {
        IslandFlags f = new IslandFlags(ring(4));
        assertEquals(String.format(KeeperFlagLines.GREETING, 4), f.talk("t0"));
        f.dye("a0", 0, 0);
        f.dye("a1", 1, 1);
        assertEquals("2 of 4 isles flagged so far.", KeeperFlagLines.line(f));
        f.dye("a2", 2, 2);
        f.dye("a3", 3, 3);
        assertEquals(Outcome.WASTEFUL, f.raise("r1"));
        assertEquals(String.format(KeeperFlagLines.WASTEFUL, 4, 2), f.talk("t1"));
        assertEquals("raise", f.quest().currentStep().type(), "no credit for a wasteful set");
        f.dye("b2", 2, 0);
        f.dye("b3", 3, 1);
        assertEquals(Outcome.WELL, f.raise("r2"));
        assertEquals(KeeperFlagLines.THANKS, f.talk("t2"));
        assertNull(f.quest().currentStep());
        assertEquals(KeeperFlagLines.DONE, f.talk("t3"));
    }
}
