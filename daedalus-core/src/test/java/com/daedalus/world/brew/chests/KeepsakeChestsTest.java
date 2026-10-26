// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.chests;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.chests.KeepsakeChests.Chest;
import com.daedalus.world.brew.chests.KeepsakeChests.Outcome;
import com.daedalus.world.brew.letters.Destination;
import java.util.List;
import org.junit.jupiter.api.Test;

class KeepsakeChestsTest {
    static KeepsakeChests seeded(long seed) {
        return KeepsakeChests.seeded(Destination.island(), seed);
    }

    static int brute(List<Keepsake> items, int cap) {
        int best = 0;
        for (int mask = 0; mask < (1 << items.size()); mask++) {
            int w = 0;
            int m = 0;
            for (int i = 0; i < items.size(); i++) {
                if ((mask >> i & 1) == 1) {
                    w += items.get(i).weight();
                    m += items.get(i).memory();
                }
            }
            if (w <= cap) {
                best = Math.max(best, m);
            }
        }
        return best;
    }

    @Test
    void oneChestPerFarIslandFamilyAndDeterministic() {
        KeepsakeChests c = seeded(4);
        assertEquals(Destination.island().size(), c.chests().size());
        for (Chest ch : c.chests()) {
            assertTrue(ch.house().size() >= 6 && ch.house().size() <= 8);
            int total = ch.house().stream().mapToInt(Keepsake::weight).sum();
            assertTrue(ch.capacity() < total, "a chest can't take the whole house");
        }
        assertEquals(c.chests(), seeded(4).chests());
        assertThrows(IllegalArgumentException.class, () -> new Keepsake("x", 0, 1));
        assertThrows(IllegalArgumentException.class, () -> new KeepsakeChests(List.of()));
    }

    @Test
    void greedyByValueIsNotEnough() {
        Chest ch = new Chest("f", List.of(new Keepsake("quilt", 6, 30), new Keepsake("fiddle", 5, 20),
                new Keepsake("letters", 5, 20)), 10);
        KeepsakeChests c = new KeepsakeChests(List.of(ch));
        assertEquals(40, c.bestMemory("f"), "two light ones beat the quilt");
        assertEquals(List.of("fiddle", "letters"), c.best("f").stream().map(Keepsake::id).toList());
    }

    @Test
    void bestMatchesBruteForce() {
        for (long seed = 0; seed < 16; seed++) {
            KeepsakeChests c = seeded(seed);
            for (Chest ch : c.chests()) {
                List<Keepsake> b = c.best(ch.family());
                assertEquals(brute(ch.house(), ch.capacity()), c.bestMemory(ch.family()), "seed " + seed);
                assertTrue(b.stream().mapToInt(Keepsake::weight).sum() <= ch.capacity());
                assertTrue(ch.house().containsAll(b));
            }
        }
    }

    @Test
    void guards() {
        Chest ch = new Chest("f", List.of(new Keepsake("a", 4, 5), new Keepsake("b", 4, 5)), 5);
        KeepsakeChests c = new KeepsakeChests(List.of(ch));
        assertEquals(Outcome.IGNORED, c.pack(" ", "f", "a"));
        assertEquals(Outcome.UNKNOWN, c.pack("e0", "nobody", "a"));
        assertEquals(Outcome.UNKNOWN, c.pack("e1", "f", "zz"));
        assertEquals(Outcome.PACKED, c.pack("e2", "f", "a"));
        assertEquals(Outcome.DUPLICATE, c.pack("e2", "f", "b"));
        assertEquals(Outcome.ALREADY_PACKED, c.pack("e3", "f", "a"));
        assertEquals(Outcome.TOO_HEAVY, c.pack("e4", "f", "b"));
        assertEquals(Outcome.NOT_PACKED, c.unpack("e5", "f", "b"));
        assertEquals(Outcome.UNPACKED, c.unpack("e6", "f", "a"));
        assertThrows(IllegalArgumentException.class,
                () -> new KeepsakeChests(List.of(new Chest("f", List.of(new Keepsake("a", 1, 1),
                        new Keepsake("a", 2, 2)), 3))));
    }

    @Test
    void questHeavyChestThenWarmThenKeeper() {
        Chest ch = new Chest("f", List.of(new Keepsake("quilt", 6, 30), new Keepsake("fiddle", 5, 20),
                new Keepsake("letters", 5, 20), new Keepsake("spoon", 1, 1)), 11);
        KeepsakeChests c = new KeepsakeChests(List.of(ch));
        assertEquals(KeeperChestLines.GREETING, c.talk("t0", "f"));
        assertEquals(Outcome.PACKED, c.pack("p1", "f", "quilt"));
        assertEquals(Outcome.PACKED, c.pack("p2", "f", "spoon"));
        assertEquals("2 in the chest, 7 of 11 weight.", KeeperChestLines.line(c, "f"));
        assertEquals(Outcome.HEAVY, c.close("c1", "f"));
        assertEquals(String.format(KeeperChestLines.HEAVY, 31, 50), c.talk("t1", "f"));
        assertEquals(Outcome.TOO_HEAVY, c.pack("p3", "f", "fiddle"));
        assertEquals(Outcome.UNPACKED, c.unpack("u1", "f", "spoon"));
        assertEquals(Outcome.PACKED, c.pack("p4", "f", "fiddle"));
        assertEquals(Outcome.WARM, c.close("c2", "f"));
        assertEquals(KeeperChestLines.THANKS, c.talk("t2", "f"));
        assertNull(c.quest().currentStep());
        assertEquals(KeeperChestLines.DONE, c.talk("t3", "f"));
    }
}
