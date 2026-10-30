// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.mats;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.mats.BeachMats.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class BeachMatsTest {
    /** Brute force: mark every covered pace. */
    static boolean[] brute(BeachMats b) {
        boolean[] sand = new boolean[32];
        for (int[] m : b.mats()) {
            for (int p = m[0]; p < m[1]; p++) {
                sand[p] = true;
            }
        }
        return sand;
    }

    /** Mats 0-4, 2-6, 6-8 (touching) and 10-12: lengths add to 12, the cover is 10. */
    static BeachMats beach() {
        return new BeachMats(List.of(new int[] {6, 8}, new int[] {0, 4}, new int[] {10, 12}, new int[] {2, 6}));
    }

    @Test
    void seededBeachIsDeterministic() {
        assertEquals(BeachMats.seeded(2).covered(), BeachMats.seeded(2).covered());
        assertEquals(BeachMats.seeded(2).mats().size(), BeachMats.seeded(2).mats().size());
        assertThrows(IllegalArgumentException.class, () -> new BeachMats(List.of(new int[] {3, 3})));
        assertThrows(IllegalArgumentException.class, () -> new BeachMats(null));
    }

    @Test
    void mergedMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            BeachMats b = BeachMats.seeded(seed);
            boolean[] sand = brute(b);
            boolean[] fromMerged = new boolean[32];
            int count = 0;
            for (boolean s : sand) {
                count += s ? 1 : 0;
            }
            int prevEnd = -1;
            for (int[] m : b.merged()) {
                assertTrue(m[0] > prevEnd, "merged spans neither overlap nor touch, seed " + seed);
                prevEnd = m[1];
                for (int p = m[0]; p < m[1]; p++) {
                    fromMerged[p] = true;
                }
            }
            assertArrayEquals(sand, fromMerged, "merged cover == brute force, seed " + seed);
            assertEquals(count, b.covered(), "seed " + seed);
        }
    }

    @Test
    void addingLengthsOvercounts() {
        BeachMats b = beach();
        assertEquals(10, b.covered());
        assertEquals(2, b.merged().size(), "touching mats join");
        assertArrayEquals(new int[] {0, 8}, b.merged().get(0));
    }

    @Test
    void miscountEarnsNoCredit() {
        BeachMats b = beach();
        b.lay("l");
        assertEquals(Outcome.MISCOUNT, b.measure("m0", 12));
        assertEquals(String.format(KeeperMatLines.MISCOUNT, 12, 10), b.talk("t0"));
        assertEquals("measure", b.quest().currentStep().type(), "no credit for a miscount");
    }

    @Test
    void guards() {
        BeachMats b = beach();
        assertEquals(Outcome.IGNORED, b.measure("", 10));
        assertEquals(Outcome.IGNORED, b.measure("e0", -1));
        assertEquals(Outcome.COVERED, b.measure("e1", 10));
        assertEquals(Outcome.DUPLICATE, b.measure("e1", 10));
        assertEquals(0, new BeachMats(List.of()).covered());
    }

    @Test
    void questMiscountThenCoveredThenKeeper() {
        BeachMats b = beach();
        assertEquals(String.format(KeeperMatLines.GREETING, 4), b.talk("t0"));
        b.lay("l0");
        assertEquals(Outcome.MISCOUNT, b.measure("m1", 12));
        assertEquals(Outcome.COVERED, b.measure("m2", 10));
        assertEquals(KeeperMatLines.THANKS, b.talk("t2"));
        assertNull(b.quest().currentStep());
        assertEquals(KeeperMatLines.DONE, b.talk("t3"));
    }
}
