// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.namestones;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.namestones.NameStones.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class NameStonesTest {
    /** Brute force: try every start of each name, shortest first, against every other name. */
    static int brute(NameStones s, int i) {
        String n = s.name(i);
        for (int k = 1; k <= n.length(); k++) {
            String start = n.substring(0, k);
            boolean clear = true;
            for (int j = 0; j < s.families(); j++) {
                clear &= j == i || !s.name(j).startsWith(start);
            }
            if (clear) {
                return k;
            }
        }
        return n.length();
    }

    /** marsh, mason, mill, oriel: mar + mas + mi + o = 9 letters; first letters alone are ambiguous. */
    static NameStones village() {
        return new NameStones(List.of("marsh", "mason", "mill", "oriel"));
    }

    @Test
    void seededVillageIsDeterministic() {
        NameStones a = NameStones.seeded(3);
        NameStones b = NameStones.seeded(3);
        assertEquals(a.families(), b.families());
        assertEquals(a.name(0), b.name(0));
        assertThrows(IllegalArgumentException.class, () -> new NameStones(List.of("mar", "marsh")));
        assertThrows(IllegalArgumentException.class, () -> new NameStones(List.of("Oriel")));
    }

    @Test
    void shortestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            NameStones s = NameStones.seeded(seed);
            int total = 0;
            for (int i = 0; i < s.families(); i++) {
                assertEquals(brute(s, i), s.shortest(i), "trie == brute force, seed " + seed + " name " + i);
                total += brute(s, i);
            }
            assertEquals(total, s.fewest(), "seed " + seed);
        }
    }

    @Test
    void knownVillage() {
        NameStones s = village();
        assertEquals(9, s.fewest());
        assertEquals(1, s.shortest(3), "oriel is the only o");
    }

    @Test
    void ambiguousStoneEarnsNoCredit() {
        NameStones s = village();
        s.list("l");
        assertEquals(Outcome.AMBIGUOUS, s.carve("c1", "m", "mas", "mi", "o"));
        assertEquals(0, s.clash());
        assertEquals(String.format(KeeperNameLines.AMBIGUOUS, "marsh"), s.talk("t1"));
        assertEquals("carve", s.quest().currentStep().type(), "no credit for an ambiguous stone");
    }

    @Test
    void guards() {
        NameStones s = village();
        assertEquals(Outcome.IGNORED, s.carve("", "mar", "mas", "mi", "o"));
        assertEquals(Outcome.NOT_THERE, s.carve("e0", "mar", "mas", "mi"));
        assertEquals(Outcome.NOT_THERE, s.carve("e0", "mar", "mas", "mo", "o"));
        assertEquals(Outcome.NOT_THERE, s.carve("e0", "mar", "mas", "", "o"));
        assertEquals(Outcome.LONG, s.carve("e1", "marsh", "mason", "mill", "oriel"));
        assertEquals(Outcome.DUPLICATE, s.carve("e1", "mar", "mas", "mi", "o"));
    }

    @Test
    void questLongThenWellThenKeeper() {
        NameStones s = village();
        assertEquals(String.format(KeeperNameLines.GREETING, 4), s.talk("t0"));
        s.list("l0");
        assertEquals(Outcome.LONG, s.carve("c1", "mars", "mas", "mi", "or"));
        assertEquals(String.format(KeeperNameLines.LONG, 11, 9), s.talk("t1"));
        assertEquals(Outcome.WELL, s.carve("c2", "mar", "mas", "mi", "o"));
        assertEquals(KeeperNameLines.THANKS, s.talk("t2"));
        assertNull(s.quest().currentStep());
        assertEquals(KeeperNameLines.DONE, s.talk("t3"));
    }
}
