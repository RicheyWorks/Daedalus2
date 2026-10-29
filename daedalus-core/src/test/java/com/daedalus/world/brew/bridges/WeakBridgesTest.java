// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.bridges;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.bridges.WeakBridges.Outcome;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

class WeakBridgesTest {
    /** Brute force: cut each bridge in turn; weak if the islets no longer all connect. */
    static Set<Integer> brute(WeakBridges w) {
        Set<Integer> out = new HashSet<>();
        if (!w.connectedWithout(-1)) {
            return out;
        }
        for (int e = 0; e < w.bridgeCount(); e++) {
            if (!w.connectedWithout(e)) {
                out.add(e);
            }
        }
        return out;
    }

    /** 0-1, 1-2, 2-0 (a loop), 2-3 and 3-4 twice (two ropes side by side). Only bridge 3 (2-3) is weak. */
    static WeakBridges islets() {
        return new WeakBridges(5, List.of(new int[] {0, 1}, new int[] {1, 2}, new int[] {2, 0}, new int[] {2, 3},
                new int[] {3, 4}, new int[] {3, 4}));
    }

    @Test
    void seededIsletsAreDeterministic() {
        assertEquals(WeakBridges.seeded(1).weak(), WeakBridges.seeded(1).weak());
        assertEquals(WeakBridges.seeded(1).islets(), WeakBridges.seeded(1).islets());
        assertThrows(IllegalArgumentException.class, () -> new WeakBridges(0, List.of()));
        assertThrows(IllegalArgumentException.class, () -> new WeakBridges(2, List.of(new int[] {1, 1})));
    }

    @Test
    void weakMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            WeakBridges w = WeakBridges.seeded(seed);
            assertEquals(brute(w), w.weak(), "Tarjan bridges == brute force, seed " + seed);
            assertEquals(w.connectedWithout(-1), w.joined(), "joined, seed " + seed);
        }
    }

    @Test
    void twinRopesAreATrap() {
        WeakBridges w = islets();
        assertEquals(Set.of(3), w.weak());
        assertEquals(Outcome.WRONG, w.mark("m0", List.of(3, 4)), "the 3-4 ropes back each other up");
        assertEquals(KeeperWeakBridges.WRONG, w.talk("t0"));
    }

    @Test
    void missedWrongAndScatteredEarnNoCredit() {
        WeakBridges chain = new WeakBridges(3, List.of(new int[] {0, 1}, new int[] {1, 2}));
        chain.cross("c");
        assertEquals(Outcome.MISSED, chain.mark("m1", List.of(0)));
        assertEquals(String.format(KeeperWeakBridges.MISSED, 1, 2), chain.talk("t1"));
        assertEquals(Outcome.MALFORMED, chain.mark("m2", List.of(0, 0)));
        assertEquals("mark", chain.quest().currentStep().type(), "no credit for a missed or wrong set");
        WeakBridges apart = new WeakBridges(3, List.of(new int[] {0, 1}));
        assertEquals(Set.of(), apart.weak());
        assertEquals(Outcome.SCATTERED, apart.mark("x", List.of(0)));
        assertEquals(KeeperWeakBridges.SCATTERED, apart.talk("tx"));
    }

    @Test
    void guards() {
        WeakBridges w = islets();
        assertEquals(Outcome.IGNORED, w.mark("", List.of(3)));
        assertEquals(Outcome.IGNORED, w.mark("e", null));
        assertEquals(Outcome.MALFORMED, w.mark("e0", List.of(6)));
        assertEquals(Outcome.EXACT, w.mark("e1", List.of(3)));
        assertEquals(Outcome.DUPLICATE, w.mark("e1", List.of(3)));
    }

    @Test
    void questWrongThenExactThenKeeper() {
        WeakBridges w = islets();
        assertEquals(String.format(KeeperWeakBridges.GREETING, 5, 6), w.talk("t0"));
        w.cross("c0");
        assertEquals(Outcome.WRONG, w.mark("m1", List.of(3, 5)));
        assertEquals(Outcome.EXACT, w.mark("m2", List.of(3)));
        assertEquals(KeeperWeakBridges.THANKS, w.talk("t2"));
        assertNull(w.quest().currentStep());
        assertEquals(KeeperWeakBridges.DONE, w.talk("t3"));
    }
}
