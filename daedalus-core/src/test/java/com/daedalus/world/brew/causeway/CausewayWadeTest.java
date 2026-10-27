// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.causeway;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.causeway.CausewayWade.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class CausewayWadeTest {
    /** Brute force: every simple path from the near corner; fewest wet cells on it. */
    static int brute(CausewayWade c) {
        int h = c.rows().size();
        int w = c.rows().get(0).length();
        return walk(c, 0, 0, new boolean[h][w], h, w);
    }

    static int walk(CausewayWade cw, int r, int c, boolean[][] seen, int h, int w) {
        int here = cw.rows().get(r).charAt(c) == '~' ? 1 : 0;
        if (r == h - 1 && c == w - 1) {
            return here;
        }
        seen[r][c] = true;
        int best = Integer.MAX_VALUE;
        int[][] moves = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
        for (int[] mv : moves) {
            int nr = r + mv[0];
            int nc = c + mv[1];
            if (nr >= 0 && nc >= 0 && nr < h && nc < w && !seen[nr][nc]) {
                best = Math.min(best, walk(cw, nr, nc, seen, h, w));
            }
        }
        seen[r][c] = false;
        return best == Integer.MAX_VALUE ? best : best + here;
    }

    /** Rows .~~ .~~ ~..: one wet step, but three on the straight route. */
    static CausewayWade fixture() {
        return new CausewayWade(List.of(".~~", ".~~", "~.."));
    }

    @Test
    void seededIsDeterministic() {
        assertEquals(CausewayWade.seeded(1).rows(), CausewayWade.seeded(1).rows());
        assertEquals(CausewayWade.seeded(1).wades(), CausewayWade.seeded(1).wades());
        assertThrows(IllegalArgumentException.class, () -> new CausewayWade(List.of()));
        assertThrows(IllegalArgumentException.class, () -> new CausewayWade(List.of("..", "x.")));
    }

    @Test
    void answerMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            CausewayWade r = CausewayWade.seeded(seed);
            assertEquals(brute(r), r.wades(), "fast == brute force, seed " + seed);
            assertTrue(r.straight() >= r.wades(), "straight route never drier, seed " + seed);
        }
    }

    @Test
    void trap() {
        CausewayWade r = fixture();
        assertEquals(1, r.wades());
        assertEquals(3, r.straight());
        assertEquals(Outcome.WRONG, r.count("c0", 3), "the straight route isn't the driest");
        assertEquals(String.format(KeeperCausewayWade.WRONG, 3), r.talk("t0"));
    }

    @Test
    void wrongAndSpecialEarnNoCredit() {
        CausewayWade r = fixture();
        r.read("r");
        assertEquals(Outcome.WRONG, r.count("c1", 1 + 1));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong answer");
        CausewayWade sp = new CausewayWade(List.of("..", ".."));
        assertTrue(sp.dry());
        assertEquals(Outcome.DRY, sp.count("x", 0));
        assertEquals(KeeperCausewayWade.DRY, sp.talk("tx"));
    }

    @Test
    void guards() {
        CausewayWade r = fixture();
        assertEquals(Outcome.IGNORED, r.count("", 1));
        assertEquals(Outcome.IGNORED, r.count(null, 1));
        assertEquals(Outcome.RIGHT, r.count("e1", 1));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 1));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        CausewayWade r = fixture();
        assertEquals(String.format(KeeperCausewayWade.GREETING, fixture().rows()), r.talk("t0"));
        r.read("r0");
        assertEquals(Outcome.WRONG, r.count("c1", 3));
        assertEquals(Outcome.RIGHT, r.count("c2", 1));
        assertEquals(KeeperCausewayWade.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperCausewayWade.DONE, r.talk("t3"));
    }
}
