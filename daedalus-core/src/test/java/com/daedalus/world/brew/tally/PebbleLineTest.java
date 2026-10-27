// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.tally;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.tally.PebbleLine.Outcome;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class PebbleLineTest {
    /** Brute force: bubble sort and count every neighbour swap. */
    static long bubble(List<Integer> sizes) {
        List<Integer> a = new ArrayList<>(sizes);
        long swaps = 0;
        for (boolean moved = true; moved;) {
            moved = false;
            for (int i = 0; i + 1 < a.size(); i++) {
                if (a.get(i) > a.get(i + 1)) {
                    a.set(i + 1, a.set(i, a.get(i + 1)));
                    swaps++;
                    moved = true;
                }
            }
        }
        return swaps;
    }

    /** Brute force: count every out-of-order pair. */
    static long pairs(List<Integer> s) {
        long c = 0;
        for (int i = 0; i < s.size(); i++) {
            for (int j = i + 1; j < s.size(); j++) {
                c += s.get(i) > s.get(j) ? 1 : 0;
            }
        }
        return c;
    }

    /** Sizes 3, 1, 2, 2: the big pebble must pass all three others, 3 swaps (ties stay put). */
    static PebbleLine line() {
        return new PebbleLine(List.of(3, 1, 2, 2));
    }

    @Test
    void seededLineIsDeterministic() {
        assertEquals(PebbleLine.seeded(5).sizes(), PebbleLine.seeded(5).sizes());
        assertThrows(IllegalArgumentException.class, () -> new PebbleLine(List.of()));
        assertThrows(IllegalArgumentException.class, () -> new PebbleLine(List.of(1001)));
    }

    @Test
    void swapsMatchBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            PebbleLine p = PebbleLine.seeded(seed);
            assertEquals(bubble(p.sizes()), p.swaps(), "Fenwick == bubble sort, seed " + seed);
            assertEquals(pairs(p.sizes()), p.swaps(), "Fenwick == pair count, seed " + seed);
        }
    }

    @Test
    void misplacedIsATrap() {
        PebbleLine p = line();
        assertEquals(3, p.swaps());
        assertEquals(Outcome.MISCOUNT, p.count("c0", 4));
        assertEquals(String.format(KeeperPebbleLines.MISCOUNT, 4, 3), p.talk("t0"));
        assertEquals(0, new PebbleLine(List.of(2, 2, 5)).swaps());
    }

    @Test
    void miscountEarnsNoCredit() {
        PebbleLine p = line();
        p.line("l");
        assertEquals(Outcome.MISCOUNT, p.count("c1", 2));
        assertEquals("count", p.quest().currentStep().type(), "no credit for a miscount");
    }

    @Test
    void guards() {
        PebbleLine p = line();
        assertEquals(Outcome.IGNORED, p.count("", 3));
        assertEquals(Outcome.IGNORED, p.count("e0", -1));
        assertEquals(Outcome.COUNTED, p.count("e1", 3));
        assertEquals(Outcome.DUPLICATE, p.count("e1", 3));
    }

    @Test
    void questMiscountThenCountedThenKeeper() {
        PebbleLine p = line();
        assertEquals(String.format(KeeperPebbleLines.GREETING, 4), p.talk("t0"));
        p.line("l0");
        assertEquals(Outcome.MISCOUNT, p.count("c1", 4));
        assertEquals(Outcome.COUNTED, p.count("c2", 3));
        assertEquals(KeeperPebbleLines.THANKS, p.talk("t2"));
        assertNull(p.quest().currentStep());
        assertEquals(KeeperPebbleLines.DONE, p.talk("t3"));
    }
}
