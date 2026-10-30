// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.doors;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.doors.LuckyDoors.Outcome;
import org.junit.jupiter.api.Test;

class LuckyDoorsTest {
    /** Brute force: add up the digits of every door. */
    static long brute(LuckyDoors d) {
        long n = 0;
        for (long x = 1; x <= d.doors(); x++) {
            if (LuckyDoors.digitSum(x) == d.luck()) {
                n++;
            }
        }
        return n;
    }

    /** Doors 1-250, lucky sum 7: 21 lucky doors; the two-digit doors alone give only 8. */
    static LuckyDoors street() {
        return new LuckyDoors(250, 7);
    }

    @Test
    void seededStreetIsDeterministic() {
        assertEquals(LuckyDoors.seeded(1).doors(), LuckyDoors.seeded(1).doors());
        assertEquals(LuckyDoors.seeded(1).lucky(), LuckyDoors.seeded(1).lucky());
        assertThrows(IllegalArgumentException.class, () -> new LuckyDoors(0, 3));
        assertThrows(IllegalArgumentException.class, () -> new LuckyDoors(10, 0));
    }

    @Test
    void luckyMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            LuckyDoors d = LuckyDoors.seeded(seed);
            assertEquals(brute(d), d.lucky(), "digit DP == brute force, seed " + seed);
        }
        assertEquals(16, new LuckyDoors(1_000_000_000_000_000L, 1).lucky(), "1, 10, ..., 10^15");
    }

    @Test
    void twoDigitDoorsOnlyIsATrap() {
        LuckyDoors d = street();
        assertEquals(21, d.lucky());
        assertEquals(Outcome.WRONG, d.count("c0", 8), "8 forgets the doors past 99");
        assertEquals(String.format(KeeperLuckyDoors.WRONG, 8), d.talk("t0"));
    }

    @Test
    void wrongAndNoLuckEarnNoCredit() {
        LuckyDoors d = street();
        d.walk("w");
        assertEquals(Outcome.WRONG, d.count("c1", 20));
        assertEquals(Outcome.MALFORMED, d.count("c2", -1));
        assertEquals("count", d.quest().currentStep().type(), "no credit for a wrong count");
        LuckyDoors none = new LuckyDoors(250, 30);
        assertEquals(0, none.lucky());
        assertEquals(Outcome.NO_LUCK, none.count("x", 0));
        assertEquals(KeeperLuckyDoors.NO_LUCK, none.talk("tx"));
    }

    @Test
    void guards() {
        LuckyDoors d = street();
        assertEquals(Outcome.IGNORED, d.count("", 21));
        assertEquals(Outcome.IGNORED, d.count(null, 21));
        assertEquals(Outcome.RIGHT, d.count("e1", 21));
        assertEquals(Outcome.DUPLICATE, d.count("e1", 21));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        LuckyDoors d = street();
        assertEquals(String.format(KeeperLuckyDoors.GREETING, 250, 7), d.talk("t0"));
        d.walk("w0");
        assertEquals(Outcome.WRONG, d.count("c1", 8));
        assertEquals(Outcome.RIGHT, d.count("c2", 21));
        assertEquals(KeeperLuckyDoors.THANKS, d.talk("t2"));
        assertNull(d.quest().currentStep());
        assertEquals(KeeperLuckyDoors.DONE, d.talk("t3"));
    }
}
