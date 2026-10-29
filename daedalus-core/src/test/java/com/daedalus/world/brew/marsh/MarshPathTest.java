// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.marsh;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.marsh.MarshPath.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class MarshPathTest {
    /** Brute force: every simple path from the near corner; fewest steps to the far corner, or -1. */
    static int brute(MarshPath m) {
        int h = m.rows().size();
        int w = m.rows().get(0).length();
        if (m.rows().get(0).charAt(0) != '.') {
            return -1;
        }
        return walk(m, 0, 0, new boolean[h][w], h, w);
    }

    static int walk(MarshPath m, int r, int c, boolean[][] seen, int h, int w) {
        if (r == h - 1 && c == w - 1) {
            return 0;
        }
        seen[r][c] = true;
        int best = -1;
        int[][] moves = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
        for (int[] mv : moves) {
            int nr = r + mv[0];
            int nc = c + mv[1];
            if (nr >= 0 && nc >= 0 && nr < h && nc < w && !seen[nr][nc] && m.rows().get(nr).charAt(nc) == '.') {
                int sub = walk(m, nr, nc, seen, h, w);
                if (sub >= 0 && (best < 0 || sub + 1 < best)) {
                    best = sub + 1;
                }
            }
        }
        seen[r][c] = false;
        return best;
    }

    /** A winding 5x3 marsh: 10 steps, though the straight line is 6. */
    static MarshPath fixture() {
        return new MarshPath(List.of("...", "~~.", "...", ".~~", "..."));
    }

    @Test
    void seededIsDeterministic() {
        assertEquals(MarshPath.seeded(1).rows(), MarshPath.seeded(1).rows());
        assertEquals(MarshPath.seeded(1).steps(), MarshPath.seeded(1).steps());
        assertThrows(IllegalArgumentException.class, () -> new MarshPath(List.of()));
        assertThrows(IllegalArgumentException.class, () -> new MarshPath(List.of("..", ".")));
    }

    @Test
    void answerMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            MarshPath r = MarshPath.seeded(seed);
            assertEquals(brute(r), r.steps(), "fast == brute force, seed " + seed);
            assertTrue(r.sunk() || r.straight() <= r.steps(), "straight line never beats the path, seed " + seed);
        }
    }

    @Test
    void trap() {
        MarshPath r = fixture();
        assertEquals(10, r.steps());
        assertEquals(6, r.straight());
        assertEquals(Outcome.WRONG, r.count("c0", 6), "pools force the path to wind");
        assertEquals(String.format(KeeperMarshPath.WRONG, 6), r.talk("t0"));
    }

    @Test
    void wrongAndSpecialEarnNoCredit() {
        MarshPath r = fixture();
        r.read("r");
        assertEquals(Outcome.WRONG, r.count("c1", 10 + 1));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong answer");
        MarshPath sp = new MarshPath(List.of(".~", "~."));
        assertTrue(sp.sunk());
        assertEquals(Outcome.SUNK, sp.count("x", 0));
        assertEquals(KeeperMarshPath.SUNK, sp.talk("tx"));
    }

    @Test
    void guards() {
        MarshPath r = fixture();
        assertEquals(Outcome.IGNORED, r.count("", 10));
        assertEquals(Outcome.IGNORED, r.count(null, 10));
        assertEquals(Outcome.RIGHT, r.count("e1", 10));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 10));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        MarshPath r = fixture();
        assertEquals(String.format(KeeperMarshPath.GREETING, List.of("...", "~~.", "...", ".~~", "...")), r.talk("t0"));
        r.read("r0");
        assertEquals(Outcome.WRONG, r.count("c1", 6));
        assertEquals(Outcome.RIGHT, r.count("c2", 10));
        assertEquals(KeeperMarshPath.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperMarshPath.DONE, r.talk("t3"));
    }
}
