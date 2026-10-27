// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.wells;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.wells.WellPipes.Outcome;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.List;
import org.junit.jupiter.api.Test;

class WellPipesTest {
    /** Brute force: flood fill over the first k pipes. */
    static int brute(WellPipes w, int k) {
        List<int[]> p = w.pipes().subList(0, k);
        boolean[] seen = new boolean[w.wells()];
        int groups = 0;
        for (int s = 0; s < w.wells(); s++) {
            if (seen[s]) {
                continue;
            }
            groups++;
            Deque<Integer> q = new ArrayDeque<>();
            q.add(s);
            seen[s] = true;
            while (!q.isEmpty()) {
                int a = q.poll();
                for (int[] e : p) {
                    int b = e[0] == a ? e[1] : e[1] == a ? e[0] : -1;
                    if (b >= 0 && !seen[b]) {
                        seen[b] = true;
                        q.add(b);
                    }
                }
            }
        }
        return groups;
    }

    /** 6 wells, 4 pipes, but 0-1, 1-2, 2-0 is a loop: 3 groups, not 6 - 4 = 2. */
    static WellPipes island() {
        return new WellPipes(6, List.of(new int[] {0, 1}, new int[] {1, 2}, new int[] {2, 0}, new int[] {3, 4}));
    }

    @Test
    void seededIslandIsDeterministic() {
        WellPipes a = WellPipes.seeded(7);
        WellPipes b = WellPipes.seeded(7);
        assertEquals(a.wells(), b.wells());
        assertEquals(a.groups(), b.groups());
        assertThrows(IllegalArgumentException.class, () -> new WellPipes(0, List.of()));
        assertThrows(IllegalArgumentException.class, () -> new WellPipes(2, List.of(new int[] {0, 2})));
    }

    @Test
    void groupsMatchBruteForceAfterEveryPipe() {
        for (long seed = 0; seed < 30; seed++) {
            WellPipes w = WellPipes.seeded(seed);
            for (int k = 0; k <= w.pipeCount(); k++) {
                assertEquals(brute(w, k), w.groupsAfter(k), "union-find == flood fill, seed " + seed + " k " + k);
            }
        }
    }

    @Test
    void loopPipeIsWasted() {
        WellPipes w = island();
        assertEquals(3, w.groups());
        assertEquals(1, w.wasted());
    }

    @Test
    void wrongCountEarnsNoCredit() {
        WellPipes w = island();
        w.walk("w");
        assertEquals(Outcome.WRONG, w.count("c1", 2));
        assertEquals(String.format(KeeperWellLines.WRONG, 2), w.talk("t1"));
        assertEquals("count", w.quest().currentStep().type(), "no credit for a wrong count");
    }

    @Test
    void guards() {
        WellPipes w = island();
        assertEquals(Outcome.IGNORED, w.count("", 3));
        assertEquals(Outcome.WRONG, w.count("e1", 6));
        assertEquals(Outcome.DUPLICATE, w.count("e1", 3));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        WellPipes w = island();
        assertEquals(String.format(KeeperWellLines.GREETING, 6, 4), w.talk("t0"));
        w.walk("w0");
        assertEquals(Outcome.WRONG, w.count("c1", 2));
        assertEquals(Outcome.RIGHT, w.count("c2", 3));
        assertEquals(KeeperWellLines.THANKS, w.talk("t2"));
        assertNull(w.quest().currentStep());
        assertEquals(KeeperWellLines.DONE, w.talk("t3"));
    }
}
