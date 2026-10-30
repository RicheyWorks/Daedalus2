package com.daedalus.world.odds;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class OddsRngTest {

    @Test
    void sameSeedSameSequence() {
        OddsRng a = new OddsRng(42);
        OddsRng b = new OddsRng(42);
        for (int i = 0; i < 100; i++) {
            assertEquals(a.nextLong(), b.nextLong());
        }
    }

    @Test
    void knownSplitMix64Vector() {
        // SplitMix64 from seed 0: the published first outputs (portable across JVMs and a C++ port).
        OddsRng r = new OddsRng(0);
        assertEquals(0xE220A8397B1DCDAFL, r.nextLong());
        assertEquals(0x6E789E6AA1B965F4L, r.nextLong());
        assertEquals(0x06C45D188009454FL, r.nextLong());
    }

    @Test
    void trialStreamsAreIndependentOfOrder() {
        long first = OddsRng.forTrial(7, 5).nextLong();
        OddsRng.forTrial(7, 1).nextLong();
        assertEquals(first, OddsRng.forTrial(7, 5).nextLong());
        assertNotEquals(OddsRng.forTrial(7, 5).nextLong(), OddsRng.forTrial(7, 6).nextLong());
        assertNotEquals(OddsRng.forTrial(7, 5).nextLong(), OddsRng.forTrial(8, 5).nextLong());
    }

    @Test
    void doublesAreInUnitIntervalAndRoughlyUniform() {
        OddsRng r = new OddsRng(99);
        double sum = 0;
        int n = 100_000;
        for (int i = 0; i < n; i++) {
            double d = r.nextDouble();
            assertTrue(d >= 0 && d < 1);
            sum += d;
        }
        assertEquals(0.5, sum / n, 0.01);
    }

    @Test
    void chanceHandlesTheEdgesAndTheMiddle() {
        OddsRng r = new OddsRng(3);
        assertFalse(r.chance(0));
        assertFalse(r.chance(-1));
        assertTrue(r.chance(1));
        assertTrue(r.chance(2));
        int hits = 0;
        for (int i = 0; i < 100_000; i++) {
            if (r.chance(0.3)) {
                hits++;
            }
        }
        assertEquals(0.3, hits / 100_000.0, 0.01);
    }
}