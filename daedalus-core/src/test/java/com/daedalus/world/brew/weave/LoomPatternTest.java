// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.weave;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.weave.LoomPattern.Outcome;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class LoomPatternTest {
    /** Brute force: try the pattern at every thread. */
    static List<Integer> brute(String s, String p) {
        List<Integer> out = new ArrayList<>();
        for (int i = 0; i + p.length() <= s.length(); i++) {
            if (s.startsWith(p, i)) {
                out.add(i);
            }
        }
        return out;
    }

    @Test
    void seededLoomIsDeterministic() {
        assertEquals(LoomPattern.seeded(7).strip(), LoomPattern.seeded(7).strip());
        assertEquals(LoomPattern.seeded(7).pattern(), LoomPattern.seeded(7).pattern());
        assertThrows(IllegalArgumentException.class, () -> new LoomPattern("ab", ""));
        assertThrows(IllegalArgumentException.class, () -> new LoomPattern(null, "a"));
    }

    @Test
    void startsMatchBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            LoomPattern l = LoomPattern.seeded(seed);
            assertEquals(brute(l.strip(), l.pattern()), l.starts(), "KMP == brute force, seed " + seed);
        }
    }

    @Test
    void overlapsCount() {
        LoomPattern l = new LoomPattern("aaaa", "aa");
        assertEquals(List.of(0, 1, 2), l.starts());
        assertEquals(List.of(0, 0, 1, 2), java.util.Arrays.stream(LoomPattern.failure("abab")).boxed().toList());
    }

    @Test
    void frayedAndMissingEarnNoCredit() {
        LoomPattern l = new LoomPattern("abaabab", "abab");
        l.weave("w");
        assertEquals(Outcome.FRAYED, l.mark("m0", 0), "aba then a: the pattern breaks");
        assertEquals(String.format(KeeperLoomLines.FRAYED, 0, 3), l.talk("t0"));
        LoomPattern none = new LoomPattern("aaa", "b");
        assertEquals(Outcome.FRAYED, none.mark("m", 0));
        assertEquals(KeeperLoomLines.MISSING, none.talk("t"));
        assertEquals("mark", l.quest().currentStep().type(), "no credit for a frayed mark");
    }

    @Test
    void guards() {
        LoomPattern l = new LoomPattern("abaabab", "abab");
        assertEquals(Outcome.IGNORED, l.mark(" ", 3));
        assertEquals(Outcome.NOT_THERE, l.mark("e0", 7));
        assertEquals(Outcome.CLEAN, l.mark("e1", 3));
        assertEquals(Outcome.DUPLICATE, l.mark("e1", 3));
    }

    @Test
    void questFrayedThenCleanThenKeeper() {
        LoomPattern l = new LoomPattern("abaabab", "abab");
        assertEquals(String.format(KeeperLoomLines.GREETING, 7, "abab"), l.talk("t0"));
        l.weave("w0");
        assertEquals(Outcome.FRAYED, l.mark("m1", 0));
        assertEquals(Outcome.CLEAN, l.mark("m2", 3));
        assertEquals(KeeperLoomLines.THANKS, l.talk("t2"));
        assertNull(l.quest().currentStep());
        assertEquals(KeeperLoomLines.DONE, l.talk("t3"));
    }
}
