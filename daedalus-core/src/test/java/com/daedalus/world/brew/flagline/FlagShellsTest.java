// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.flagline;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.flagline.FlagShells.Outcome;
import java.util.ArrayDeque;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;

class FlagShellsTest {
    /** Brute force: breadth-first search over every line reachable by swaps until the flag appears. */
    static int brute(FlagShells f) {
        Map<String, Integer> dist = new HashMap<>();
        ArrayDeque<String> todo = new ArrayDeque<>();
        dist.put(f.line(), 0);
        todo.add(f.line());
        while (!todo.isEmpty()) {
            String s = todo.poll();
            if (s.equals(f.sorted())) {
                return dist.get(s);
            }
            for (int i = 0; i < s.length(); i++) {
                for (int j = i + 1; j < s.length(); j++) {
                    char[] c = s.toCharArray();
                    char t = c[i];
                    c[i] = c[j];
                    c[j] = t;
                    String n = new String(c);
                    if (!dist.containsKey(n)) {
                        dist.put(n, dist.get(s) + 1);
                        todo.add(n);
                    }
                }
            }
        }
        return -1;
    }

    /** BWRWRB: 4 shells out of place, but two direct trades make RRWWBB in 2 swaps. */
    static FlagShells shells() {
        return new FlagShells("BWRWRB");
    }

    @Test
    void seededLineIsDeterministic() {
        assertEquals(FlagShells.seeded(1).line(), FlagShells.seeded(1).line());
        assertEquals("RRWWBB", shells().sorted());
        assertThrows(IllegalArgumentException.class, () -> new FlagShells(""));
        assertThrows(IllegalArgumentException.class, () -> new FlagShells("RGB"));
    }

    @Test
    void fewestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            FlagShells f = FlagShells.seeded(seed);
            assertEquals(brute(f), f.fewest(), "swap counting == brute force, seed " + seed);
        }
    }

    @Test
    void onePerMisplacedShellIsATrap() {
        FlagShells f = shells();
        assertEquals(2, f.fewest());
        assertEquals(2, new FlagShells("BRW").fewest(), "a three-way muddle takes 2");
        assertEquals(Outcome.WRONG, f.count("c0", 4), "4 shells are misplaced, but each swap fixes two");
        assertEquals(String.format(KeeperFlagShells.WRONG, 4), f.talk("t0"));
    }

    @Test
    void wrongAndAlreadyFlagEarnNoCredit() {
        FlagShells f = shells();
        f.lay("l");
        assertEquals(Outcome.WRONG, f.count("c1", 3));
        assertEquals(Outcome.MALFORMED, f.count("c2", -1));
        assertEquals("count", f.quest().currentStep().type(), "no credit for a wrong count");
        FlagShells done = new FlagShells("RWWB");
        assertEquals(0, done.fewest());
        assertEquals(Outcome.ALREADY_FLAG, done.count("x", 0));
        assertEquals(KeeperFlagShells.ALREADY_FLAG, done.talk("tx"));
    }

    @Test
    void guards() {
        FlagShells f = shells();
        assertEquals(Outcome.IGNORED, f.count("", 2));
        assertEquals(Outcome.IGNORED, f.count(null, 2));
        assertEquals(Outcome.RIGHT, f.count("e1", 2));
        assertEquals(Outcome.DUPLICATE, f.count("e1", 2));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        FlagShells f = shells();
        assertEquals(String.format(KeeperFlagShells.GREETING, "BWRWRB"), f.talk("t0"));
        f.lay("l0");
        assertEquals(Outcome.WRONG, f.count("c1", 4));
        assertEquals(Outcome.RIGHT, f.count("c2", 2));
        assertEquals(KeeperFlagShells.THANKS, f.talk("t2"));
        assertNull(f.quest().currentStep());
        assertEquals(KeeperFlagShells.DONE, f.talk("t3"));
    }
}
