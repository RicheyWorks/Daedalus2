// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.spans;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.spans.DrumLines.Outcome;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

class DrumLinesTest {
    /** Brute force: every subset of lines; the least rope among those that link every hut. */
    static long brute(DrumLines d) {
        int m = d.lines().size();
        long best = DrumLines.NONE;
        for (int mask = 0; mask < 1 << m; mask++) {
            Set<Integer> s = new HashSet<>();
            long rope = 0;
            for (int i = 0; i < m; i++) {
                if ((mask >> i & 1) == 1) {
                    s.add(i);
                    rope += d.lines().get(i)[2];
                }
            }
            if (d.links(s) && (best == DrumLines.NONE || rope < best)) {
                best = rope;
            }
        }
        return best;
    }

    /** Lines 0-1:1, 1-2:2, 0-2:2, 2-3:5, 1-3:4. Cheapest 1+2+4 = 7; the three cheapest lines leave hut 3 out. */
    static DrumLines village() {
        return new DrumLines(4, List.of(new int[] {0, 1, 1}, new int[] {1, 2, 2}, new int[] {0, 2, 2},
                new int[] {2, 3, 5}, new int[] {1, 3, 4}));
    }

    @Test
    void seededVillageIsDeterministic() {
        assertEquals(DrumLines.seeded(1).cheapest(), DrumLines.seeded(1).cheapest());
        assertEquals(DrumLines.seeded(1).huts(), DrumLines.seeded(1).huts());
        assertThrows(IllegalArgumentException.class, () -> new DrumLines(0, List.of()));
        assertThrows(IllegalArgumentException.class, () -> new DrumLines(2, List.of(new int[] {0, 0, 1})));
    }

    @Test
    void cheapestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            DrumLines d = DrumLines.seeded(seed);
            assertEquals(brute(d), d.cheapest(), "Kruskal == brute force, seed " + seed);
        }
    }

    @Test
    void cheapLinesFirstIsATrap() {
        DrumLines d = village();
        assertEquals(7, d.cheapest());
        assertEquals(Outcome.BROKEN, d.string("s0", List.of(0, 1, 2)), "hut 3 left out");
        assertEquals(KeeperDrumLines.BROKEN, d.talk("t0"));
    }

    @Test
    void dearBrokenAndCutOffEarnNoCredit() {
        DrumLines d = village();
        d.survey("v");
        assertEquals(Outcome.DEAR, d.string("s1", List.of(0, 1, 3)));
        assertEquals(String.format(KeeperDrumLines.DEAR, 8, 7), d.talk("t1"));
        assertEquals(Outcome.MALFORMED, d.string("s2", List.of(0, 0)));
        assertEquals("string", d.quest().currentStep().type(), "no credit for a dear or broken net");
        DrumLines cut = new DrumLines(3, List.of(new int[] {0, 1, 1}));
        assertEquals(DrumLines.NONE, cut.cheapest());
        assertEquals(Outcome.CUT_OFF, cut.string("x", List.of(0)));
        assertEquals(KeeperDrumLines.CUT_OFF, cut.talk("tx"));
    }

    @Test
    void guards() {
        DrumLines d = village();
        assertEquals(Outcome.IGNORED, d.string("", List.of(0, 1, 4)));
        assertEquals(Outcome.IGNORED, d.string("e", null));
        assertEquals(Outcome.MALFORMED, d.string("e0", List.of(5)));
        assertEquals(Outcome.CHEAPEST, d.string("e1", List.of(0, 1, 4)));
        assertEquals(Outcome.DUPLICATE, d.string("e1", List.of(0, 1, 4)));
    }

    @Test
    void questDearThenCheapestThenKeeper() {
        DrumLines d = village();
        assertEquals(String.format(KeeperDrumLines.GREETING, 4, 5), d.talk("t0"));
        d.survey("v0");
        assertEquals(Outcome.DEAR, d.string("s1", List.of(0, 1, 3)));
        assertEquals(Outcome.CHEAPEST, d.string("s2", List.of(4, 2, 0)));
        assertEquals(KeeperDrumLines.THANKS, d.talk("t2"));
        assertNull(d.quest().currentStep());
        assertEquals(KeeperDrumLines.DONE, d.talk("t3"));
    }
}
