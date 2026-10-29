// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.purse;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.purse.ShellPurse.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class ShellPurseTest {
    /** Brute force: choose how many of each shell, coin by coin. */
    static int brute(ShellPurse p) {
        return pick(p.coins(), 0, p.total());
    }

    static int pick(List<Integer> coins, int i, int left) {
        if (i == coins.size()) {
            return left == 0 ? 1 : 0;
        }
        int n = 0;
        for (int k = 0; k * coins.get(i) <= left; k++) {
            n += pick(coins, i + 1, left - k * coins.get(i));
        }
        return n;
    }

    /** Brute force for orders: every first shell, then the rest. */
    static int seqs(List<Integer> coins, int left) {
        if (left == 0) {
            return 1;
        }
        int n = 0;
        for (int c : coins) {
            if (c <= left) {
                n += seqs(coins, left - c);
            }
        }
        return n;
    }

    /** Shells 1 and 2, price 4: three handfuls (1111, 112, 22), but five orders. */
    static ShellPurse fixture() {
        return new ShellPurse(List.of(1, 2), 4);
    }

    @Test
    void seededIsDeterministic() {
        assertEquals(ShellPurse.seeded(1).coins(), ShellPurse.seeded(1).coins());
        assertEquals(ShellPurse.seeded(1).ways(), ShellPurse.seeded(1).ways());
        assertThrows(IllegalArgumentException.class, () -> new ShellPurse(List.of(), 1));
        assertThrows(IllegalArgumentException.class, () -> new ShellPurse(List.of(2, 2), 1));
    }

    @Test
    void answerMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            ShellPurse r = ShellPurse.seeded(seed);
            assertEquals(brute(r), r.ways(), "fast == brute force, seed " + seed);
            assertEquals(seqs(r.coins(), r.total()), r.orders(), "orders, seed " + seed);
            assertTrue(r.orders() >= r.ways(), "orders never fewer than handfuls, seed " + seed);
        }
    }

    @Test
    void trap() {
        ShellPurse r = fixture();
        assertEquals(3, r.ways());
        assertEquals(5, r.orders());
        assertEquals(Outcome.WRONG, r.count("c0", 5), "counting orders counts the same handful twice");
        assertEquals(String.format(KeeperShellPurse.WRONG, 5), r.talk("t0"));
    }

    @Test
    void wrongAndSpecialEarnNoCredit() {
        ShellPurse r = fixture();
        r.read("r");
        assertEquals(Outcome.WRONG, r.count("c1", 3 + 1));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong answer");
        ShellPurse sp = new ShellPurse(List.of(2), 3);
        assertTrue(sp.unpayable());
        assertEquals(Outcome.UNPAYABLE, sp.count("x", 0));
        assertEquals(KeeperShellPurse.UNPAYABLE, sp.talk("tx"));
    }

    @Test
    void guards() {
        ShellPurse r = fixture();
        assertEquals(Outcome.IGNORED, r.count("", 3));
        assertEquals(Outcome.IGNORED, r.count(null, 3));
        assertEquals(Outcome.RIGHT, r.count("e1", 3));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 3));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        ShellPurse r = fixture();
        assertEquals(String.format(KeeperShellPurse.GREETING, List.of(1, 2), 4), r.talk("t0"));
        r.read("r0");
        assertEquals(Outcome.WRONG, r.count("c1", 5));
        assertEquals(Outcome.RIGHT, r.count("c2", 3));
        assertEquals(KeeperShellPurse.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperShellPurse.DONE, r.talk("t3"));
    }
}
