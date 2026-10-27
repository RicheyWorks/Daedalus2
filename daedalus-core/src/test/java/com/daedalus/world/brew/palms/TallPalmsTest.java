// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.palms;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.palms.TallPalms.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class TallPalmsTest {
    /** Brute force: scan forward from each palm. */
    static int brute(List<Integer> h, int i) {
        for (int j = i + 1; j < h.size(); j++) {
            if (h.get(j) > h.get(i)) {
                return j;
            }
        }
        return TallPalms.NONE;
    }

    /** Heights 4, 2, 4, 5, 9 with the climber on palm 0: equal palm 2 is not taller;
     * the tallest, palm 4, is not first. */
    static TallPalms shore() {
        return new TallPalms(List.of(4, 2, 4, 5, 9), 0);
    }

    @Test
    void seededShoreIsDeterministic() {
        assertEquals(TallPalms.seeded(2).heights(), TallPalms.seeded(2).heights());
        assertEquals(TallPalms.seeded(2).asked(), TallPalms.seeded(2).asked());
        assertThrows(IllegalArgumentException.class, () -> new TallPalms(List.of(3), 1));
        assertThrows(IllegalArgumentException.class, () -> new TallPalms(List.of(0), 0));
    }

    @Test
    void nextTallerMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            TallPalms p = TallPalms.seeded(seed);
            for (int i = 0; i < p.palms(); i++) {
                assertEquals(brute(p.heights(), i), p.nextTaller(i), "stack == brute force, seed " + seed + " palm " + i);
            }
        }
    }

    @Test
    void equalAndTallestAreTraps() {
        TallPalms p = shore();
        assertEquals(3, p.nextTaller(0));
        assertEquals(TallPalms.NONE, p.nextTaller(4));
        assertEquals(Outcome.WRONG, p.name("n0", 2));
        assertEquals(String.format(KeeperPalmLines.WRONG, 2, "palm 3"), p.talk("t0"));
    }

    @Test
    void wrongEarnsNoCredit() {
        TallPalms p = shore();
        p.walk("w");
        assertEquals(Outcome.WRONG, p.name("n1", 4));
        assertEquals("name", p.quest().currentStep().type(), "no credit for a wrong palm");
        TallPalms last = new TallPalms(List.of(3, 9), 1);
        assertEquals(Outcome.WRONG, last.name("x", 0));
        assertEquals(String.format(KeeperPalmLines.WRONG, 0, "no palm at all"), last.talk("tx"));
        assertEquals(Outcome.RIGHT, last.name("y", TallPalms.NONE));
    }

    @Test
    void guards() {
        TallPalms p = shore();
        assertEquals(Outcome.IGNORED, p.name("", 3));
        assertEquals(Outcome.IGNORED, p.name("e0", 5));
        assertEquals(Outcome.RIGHT, p.name("e1", 3));
        assertEquals(Outcome.DUPLICATE, p.name("e1", 3));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        TallPalms p = shore();
        assertEquals(String.format(KeeperPalmLines.GREETING, 5, 0), p.talk("t0"));
        p.walk("w0");
        assertEquals(Outcome.WRONG, p.name("n1", 4));
        assertEquals(Outcome.RIGHT, p.name("n2", 3));
        assertEquals(KeeperPalmLines.THANKS, p.talk("t2"));
        assertNull(p.quest().currentStep());
        assertEquals(KeeperPalmLines.DONE, p.talk("t3"));
    }
}
