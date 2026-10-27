// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.shelves;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.shelves.JarShelves.Outcome;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class JarShelvesTest {
    /** Brute force: breadth-first search over shelf orders, one swap per step. */
    static int brute(JarShelves s) {
        List<Integer> goal = new ArrayList<>(s.order());
        Collections.sort(goal);
        Map<List<Integer>, Integer> dist = new HashMap<>();
        ArrayDeque<List<Integer>> q = new ArrayDeque<>();
        dist.put(s.order(), 0);
        q.add(s.order());
        while (!q.isEmpty()) {
            List<Integer> u = q.poll();
            if (u.equals(goal)) {
                return dist.get(u);
            }
            for (int i = 0; i < u.size(); i++) {
                for (int j = i + 1; j < u.size(); j++) {
                    List<Integer> v = new ArrayList<>(u);
                    Collections.swap(v, i, j);
                    if (!dist.containsKey(v)) {
                        dist.put(v, dist.get(u) + 1);
                        q.add(v);
                    }
                }
            }
        }
        return -1;
    }

    /** Shelf 1 2 0: one ring of three jars, 2 swaps, though 3 are misplaced. */
    static JarShelves fixture() {
        return new JarShelves(List.of(1, 2, 0));
    }

    @Test
    void seededIsDeterministic() {
        assertEquals(JarShelves.seeded(1).order(), JarShelves.seeded(1).order());
        assertEquals(JarShelves.seeded(1).swaps(), JarShelves.seeded(1).swaps());
        assertThrows(IllegalArgumentException.class, () -> new JarShelves(List.of()));
        assertThrows(IllegalArgumentException.class, () -> new JarShelves(List.of(0, 0)));
    }

    @Test
    void answerMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            JarShelves r = JarShelves.seeded(seed);
            assertEquals(brute(r), r.swaps(), "fast == brute force, seed " + seed);
            assertTrue(r.misplaced() >= r.swaps(), "never more swaps than misplaced jars, seed " + seed);
        }
    }

    @Test
    void trap() {
        JarShelves r = fixture();
        assertEquals(2, r.swaps());
        assertEquals(3, r.misplaced());
        assertEquals(Outcome.WRONG, r.count("c0", 3), "a ring needs one swap fewer than its size");
        assertEquals(String.format(KeeperJarShelves.WRONG, 3), r.talk("t0"));
    }

    @Test
    void wrongAndSpecialEarnNoCredit() {
        JarShelves r = fixture();
        r.read("r");
        assertEquals(Outcome.WRONG, r.count("c1", 2 + 1));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong answer");
        JarShelves sp = new JarShelves(List.of(0, 1, 2));
        assertTrue(sp.sorted());
        assertEquals(Outcome.SORTED, sp.count("x", 0));
        assertEquals(KeeperJarShelves.SORTED, sp.talk("tx"));
    }

    @Test
    void guards() {
        JarShelves r = fixture();
        assertEquals(Outcome.IGNORED, r.count("", 2));
        assertEquals(Outcome.IGNORED, r.count(null, 2));
        assertEquals(Outcome.RIGHT, r.count("e1", 2));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 2));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        JarShelves r = fixture();
        assertEquals(String.format(KeeperJarShelves.GREETING, List.of(1, 2, 0)), r.talk("t0"));
        r.read("r0");
        assertEquals(Outcome.WRONG, r.count("c1", 3));
        assertEquals(Outcome.RIGHT, r.count("c2", 2));
        assertEquals(KeeperJarShelves.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperJarShelves.DONE, r.talk("t3"));
    }
}
