// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.buckets;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.buckets.TwoBuckets.Outcome;
import org.junit.jupiter.api.Test;

class TwoBucketsTest {
    /** Brute force: relax every move from every state until nothing changes, then take the best target state. */
    static int brute(TwoBuckets t) {
        int a = t.bucketA();
        int b = t.bucketB();
        int inf = Integer.MAX_VALUE / 2;
        int[][] d = new int[a + 1][b + 1];
        for (int[] row : d) {
            java.util.Arrays.fill(row, inf);
        }
        d[0][0] = 0;
        boolean changed = true;
        while (changed) {
            changed = false;
            for (int x = 0; x <= a; x++) {
                for (int y = 0; y <= b; y++) {
                    if (d[x][y] == inf) {
                        continue;
                    }
                    for (String m : TwoBuckets.MOVES) {
                        int[] s = t.step(new int[] {x, y}, m);
                        if (d[x][y] + 1 < d[s[0]][s[1]]) {
                            d[s[0]][s[1]] = d[x][y] + 1;
                            changed = true;
                        }
                    }
                }
            }
        }
        int best = inf;
        for (int x = 0; x <= a; x++) {
            for (int y = 0; y <= b; y++) {
                if (x == t.target() || y == t.target()) {
                    best = Math.min(best, d[x][y]);
                }
            }
        }
        return best == inf ? -1 : best;
    }

    static TwoBuckets classic() {
        return new TwoBuckets(3, 5, 4);
    }

    @Test
    void seededBucketsAreDeterministic() {
        TwoBuckets x = TwoBuckets.seeded(6);
        TwoBuckets y = TwoBuckets.seeded(6);
        assertEquals(x.target(), y.target());
        assertEquals(x.fewest(), y.fewest());
        assertThrows(IllegalArgumentException.class, () -> new TwoBuckets(3, 5, 6));
        assertEquals(-1, new TwoBuckets(2, 4, 3).fewest(), "even buckets never make 3");
    }

    @Test
    void fewestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            TwoBuckets t = TwoBuckets.seeded(seed);
            assertEquals(brute(t), t.fewest(), "BFS == brute relaxation, seed " + seed);
        }
    }

    @Test
    void startingWithTheSmallBucketIsLonger() {
        TwoBuckets t = classic();
        assertEquals(6, t.fewest());
        assertEquals(Outcome.LONG, t.measure("s", "FA", "AB", "FA", "AB", "EB", "AB", "FA", "AB"));
        assertEquals(8, t.used());
    }

    @Test
    void missedMeasureEarnsNoCredit() {
        TwoBuckets t = classic();
        t.fetch("f");
        assertEquals(Outcome.MISSED, t.measure("m1", "FB", "BA"));
        assertEquals(String.format(KeeperBucketLines.MISSED, 4), t.talk("t1"));
        assertEquals("measure", t.quest().currentStep().type(), "no credit for a miss");
    }

    @Test
    void guards() {
        TwoBuckets t = classic();
        assertEquals(Outcome.IGNORED, t.measure("", "FA"));
        assertEquals(Outcome.NOT_THERE, t.measure("e0", "FA", "XX"));
        assertEquals(Outcome.MISSED, t.measure("e1"));
        assertEquals(Outcome.DUPLICATE, t.measure("e1", "FB"));
    }

    @Test
    void questLongThenWellThenKeeper() {
        TwoBuckets t = classic();
        assertEquals(String.format(KeeperBucketLines.GREETING, 3, 5, 4), t.talk("t0"));
        t.fetch("f0");
        assertEquals(Outcome.LONG, t.measure("m1", "FA", "AB", "FA", "AB", "EB", "AB", "FA", "AB"));
        assertEquals(String.format(KeeperBucketLines.LONG, 8, 6), t.talk("t1"));
        assertEquals(Outcome.WELL, t.measure("m2", "FB", "BA", "EA", "BA", "FB", "BA"));
        assertEquals(KeeperBucketLines.THANKS, t.talk("t2"));
        assertNull(t.quest().currentStep());
        assertEquals(KeeperBucketLines.DONE, t.talk("t3"));
    }
}
