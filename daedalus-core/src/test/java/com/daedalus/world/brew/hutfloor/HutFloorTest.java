// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.hutfloor;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.hutfloor.HutFloor.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class HutFloorTest {
    /** Brute force: lay a mat across or down at the first bare square, every way, and count full covers. */
    static long brute(HutFloor f) {
        int h = f.rows().size();
        int w = f.width();
        boolean[][] used = new boolean[h][w];
        for (int r = 0; r < h; r++) {
            for (int c = 0; c < w; c++) {
                used[r][c] = f.rows().get(r).charAt(c) == '#';
            }
        }
        return lay(used, h, w);
    }

    static long lay(boolean[][] used, int h, int w) {
        for (int r = 0; r < h; r++) {
            for (int c = 0; c < w; c++) {
                if (!used[r][c]) {
                    long n = 0;
                    used[r][c] = true;
                    if (c + 1 < w && !used[r][c + 1]) {
                        used[r][c + 1] = true;
                        n += lay(used, h, w);
                        used[r][c + 1] = false;
                    }
                    if (r + 1 < h && !used[r + 1][c]) {
                        used[r + 1][c] = true;
                        n += lay(used, h, w);
                        used[r + 1][c] = false;
                    }
                    used[r][c] = false;
                    return n;
                }
            }
        }
        return 1;
    }

    /** A 3x4 floor with posts in two far corners: 5 layouts; a bare 3x4 floor has 11. */
    static HutFloor floor() {
        return new HutFloor(List.of("#...", "....", "...#"));
    }

    @Test
    void seededFloorIsDeterministic() {
        assertEquals(HutFloor.seeded(1).rows(), HutFloor.seeded(1).rows());
        assertEquals(HutFloor.seeded(1).ways(), HutFloor.seeded(1).ways());
        assertThrows(IllegalArgumentException.class, () -> new HutFloor(List.of("..", "...")));
        assertThrows(IllegalArgumentException.class, () -> new HutFloor(List.of(".x")));
    }

    @Test
    void waysMatchBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            HutFloor f = HutFloor.seeded(seed);
            assertEquals(brute(f), f.ways(), "bitmask DP == brute force, seed " + seed);
        }
        assertEquals(11, new HutFloor(List.of("....", "....", "....")).ways());
    }

    @Test
    void bareFloorCountIsATrap() {
        HutFloor f = floor();
        assertEquals(5, f.ways());
        assertEquals(Outcome.WRONG, f.count("c0", 11), "11 is the bare floor, ignoring the posts");
        assertEquals(String.format(KeeperHutFloor.WRONG, 11), f.talk("t0"));
    }

    @Test
    void wrongAndNoFitEarnNoCredit() {
        HutFloor f = floor();
        f.sweep("s");
        assertEquals(Outcome.WRONG, f.count("c1", 4));
        assertEquals(Outcome.MALFORMED, f.count("c2", -1));
        assertEquals("count", f.quest().currentStep().type(), "no credit for a wrong count");
        HutFloor corners = new HutFloor(List.of("#..", "...", "..#"));
        assertEquals(0, corners.ways(), "eight bare squares, but two posts on the same colour");
        assertEquals(Outcome.NO_FIT, corners.count("x", 0));
        assertEquals(KeeperHutFloor.NO_FIT, corners.talk("tx"));
    }

    @Test
    void guards() {
        HutFloor f = floor();
        assertEquals(Outcome.IGNORED, f.count("", 5));
        assertEquals(Outcome.IGNORED, f.count(null, 5));
        assertEquals(Outcome.RIGHT, f.count("e1", 5));
        assertEquals(Outcome.DUPLICATE, f.count("e1", 5));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        HutFloor f = floor();
        assertEquals(String.format(KeeperHutFloor.GREETING, 3, 4), f.talk("t0"));
        f.sweep("s0");
        assertEquals(Outcome.WRONG, f.count("c1", 11));
        assertEquals(Outcome.RIGHT, f.count("c2", 5));
        assertEquals(KeeperHutFloor.THANKS, f.talk("t2"));
        assertNull(f.quest().currentStep());
        assertEquals(KeeperHutFloor.DONE, f.talk("t3"));
    }
}
