// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.bells;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.bells.BellTower.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class BellTowerTest {
    /** Brute force: count beats until every bell rings. */
    static long brute(List<Integer> periods) {
        for (long t = 1;; t++) {
            boolean all = true;
            for (int p : periods) {
                all &= t % p == 0;
            }
            if (all) {
                return t;
            }
        }
    }

    /** Bells of 4, 6 and 9: they meet at 36, not at 4 x 6 x 9 = 216; beat 12 misses the 9. */
    static BellTower tower() {
        return new BellTower(List.of(4, 6, 9));
    }

    @Test
    void seededTowerIsDeterministic() {
        assertEquals(BellTower.seeded(5).periods(), BellTower.seeded(5).periods());
        assertThrows(IllegalArgumentException.class, () -> new BellTower(List.of()));
        assertThrows(IllegalArgumentException.class, () -> new BellTower(List.of(3, 0)));
    }

    @Test
    void togetherMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            BellTower b = BellTower.seeded(seed);
            assertEquals(brute(b.periods()), b.together(), "lcm == brute force, seed " + seed);
        }
        assertEquals(6, BellTower.gcd(12, 18));
    }

    @Test
    void productIsLate() {
        BellTower b = tower();
        assertEquals(36, b.together());
        assertEquals(Outcome.LATE, b.name("n0", 216));
        assertEquals(String.format(KeeperBellLines.LATE, 216, 36), b.talk("t0"));
    }

    @Test
    void offbeatEarnsNoCredit() {
        BellTower b = tower();
        b.listen("l");
        assertEquals(Outcome.OFFBEAT, b.name("n1", 12));
        assertEquals(String.format(KeeperBellLines.OFFBEAT, 12), b.talk("t1"));
        assertEquals("name", b.quest().currentStep().type(), "no credit for an offbeat");
    }

    @Test
    void guards() {
        BellTower b = tower();
        assertEquals(Outcome.IGNORED, b.name("", 36));
        assertEquals(Outcome.IGNORED, b.name("e0", 0));
        assertEquals(Outcome.TOGETHER, b.name("e1", 36));
        assertEquals(Outcome.DUPLICATE, b.name("e1", 36));
    }

    @Test
    void questOffbeatThenTogetherThenKeeper() {
        BellTower b = tower();
        assertEquals(String.format(KeeperBellLines.GREETING, 3), b.talk("t0"));
        b.listen("l0");
        assertEquals(Outcome.OFFBEAT, b.name("n1", 12));
        assertEquals(Outcome.TOGETHER, b.name("n2", 36));
        assertEquals(KeeperBellLines.THANKS, b.talk("t2"));
        assertNull(b.quest().currentStep());
        assertEquals(KeeperBellLines.DONE, b.talk("t3"));
    }
}
