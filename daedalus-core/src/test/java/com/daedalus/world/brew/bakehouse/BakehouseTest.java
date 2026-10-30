// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.bakehouse;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.bakehouse.Bakehouse.Outcome;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class BakehouseTest {
    /** Brute force over every loaf order. */
    static int brute(Bakehouse b) {
        int[] best = {Integer.MAX_VALUE};
        perm(b, new ArrayList<>(), best);
        return best[0];
    }

    private static void perm(Bakehouse b, List<Integer> o, int[] best) {
        if (o.size() == b.loaves()) {
            best[0] = Math.min(best[0], b.finish(o));
            return;
        }
        for (int i = 0; i < b.loaves(); i++) {
            if (!o.contains(i)) {
                o.add(i);
                perm(b, o, best);
                o.remove(o.size() - 1);
            }
        }
    }

    static Bakehouse pair() {
        return new Bakehouse(new int[] {5, 1}, new int[] {1, 5});
    }

    @Test
    void seededBatchIsDeterministic() {
        Bakehouse b = Bakehouse.seeded(2);
        assertTrue(b.loaves() >= 3 && b.loaves() <= 7);
        assertEquals(b.soonest(), Bakehouse.seeded(2).soonest());
        assertThrows(IllegalArgumentException.class, () -> new Bakehouse(new int[] {0}, new int[] {1}));
    }

    @Test
    void soonestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            Bakehouse b = Bakehouse.seeded(seed);
            assertEquals(brute(b), b.soonest(), "Johnson == brute force, seed " + seed);
        }
    }

    @Test
    void quickKneadsGoFirst() {
        Bakehouse b = pair();
        assertEquals(7, b.soonest());
        assertEquals(11, b.finish(List.of(0, 1)));
    }

    @Test
    void lateEarnsNoCredit() {
        Bakehouse b = pair();
        b.queue("q1", 0);
        assertEquals(Outcome.UNFINISHED, b.bake("b0"));
        b.queue("q2", 1);
        assertEquals(Outcome.LATE, b.bake("b1"));
        assertEquals("bake", b.quest().currentStep().type(), "no credit for a late batch");
    }

    @Test
    void guards() {
        Bakehouse b = pair();
        assertEquals(Outcome.IGNORED, b.queue("", 0));
        assertEquals(Outcome.NOT_THERE, b.queue("e0", 2));
        assertEquals(Outcome.QUEUED, b.queue("e1", 0));
        assertEquals(Outcome.DUPLICATE, b.queue("e1", 1));
        assertEquals(Outcome.ALREADY, b.queue("e2", 0));
    }

    @Test
    void questLateThenWellThenKeeper() {
        Bakehouse b = pair();
        assertEquals(String.format(KeeperBakeLines.GREETING, 2), b.talk("t0"));
        b.queue("a1", 0);
        assertEquals("1 of 2 loaves in the queue.", KeeperBakeLines.line(b));
        b.queue("a2", 1);
        assertEquals(Outcome.LATE, b.bake("b1"));
        assertEquals(String.format(KeeperBakeLines.LATE, 11, 7), b.talk("t1"));
        b.restart();
        b.queue("c1", 1);
        b.queue("c2", 0);
        assertEquals(Outcome.WELL, b.bake("b2"));
        assertEquals(KeeperBakeLines.THANKS, b.talk("t2"));
        assertNull(b.quest().currentStep());
        assertEquals(KeeperBakeLines.DONE, b.talk("t3"));
    }
}
