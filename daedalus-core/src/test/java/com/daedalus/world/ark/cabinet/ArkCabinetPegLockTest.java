// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.ark.PegBoard;
import java.util.HashMap;
import java.util.Map;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class ArkCabinetPegLockTest {

    /** Brute force: true when some jump sequence leaves one peg. */
    private static boolean clearable(int board, int[][] js, Map<Integer, Boolean> memo) {
        if (Integer.bitCount(board) == 1) {
            return true;
        }
        Boolean got = memo.get(board);
        if (got != null) {
            return got;
        }
        boolean ok = false;
        for (int[] j : js) {
            if (!ok && (board >> j[0] & 1) == 1 && (board >> j[1] & 1) == 1 && (board >> j[2] & 1) == 0) {
                ok = clearable(board & ~(1 << j[0]) & ~(1 << j[1]) | (1 << j[2]), js, memo);
            }
        }
        memo.put(board, ok);
        return ok;
    }

    /** Brute force Mastermind score: exact * 10 + colour-only. */
    private static int bruteScore(int secret, int guess) {
        int[] a = new int[4];
        int[] b = new int[4];
        for (int i = 0, x = secret, y = guess; i < 4; i++, x /= 6, y /= 6) {
            a[i] = x % 6;
            b[i] = y % 6;
        }
        int exact = 0;
        int[] ca = new int[6];
        int[] cb = new int[6];
        for (int i = 0; i < 4; i++) {
            if (a[i] == b[i]) {
                exact++;
            } else {
                ca[a[i]]++;
                cb[b[i]]++;
            }
        }
        int colour = 0;
        for (int c = 0; c < 6; c++) {
            colour += Math.min(ca[c], cb[c]);
        }
        return exact * 10 + colour;
    }

    @Test
    void pegBoardAutoplayClearsExactlyTheSolvableHoles() {
        for (int side = 4; side <= 5; side++) {
            int holes = side * (side + 1) / 2;
            int[][] js = PegBoard.jumps(side);
            Map<Integer, Boolean> memo = new HashMap<>();
            for (int hole = 0; hole < holes; hole++) {
                boolean can = clearable(((1 << holes) - 1) & ~(1 << hole), js, memo);
                PegBoardGame g = new PegBoardGame(side, hole);
                ArkCabinet.autoplay(g);
                assertThat(g.over()).isTrue();
                assertThat(g.winner() == 1).as("side %d hole %d", side, hole).isEqualTo(can);
            }
        }
        PegBoardGame g = new PegBoardGame();
        assertThat(g.onSolverLine()).isTrue();
        assertThat(ArkCabinet.autoplay(g)).hasSize(13);
        assertThat(g.pegs()).isEqualTo(1);
        assertThat(g.render()).contains("cleared!");
    }

    @Test
    void pegBoardRejectsBadJumpsAndLeavesTheSolverLine() {
        PegBoardGame g = new PegBoardGame();
        assertThat(g.legalMoves()).containsExactlyInAnyOrder("4,1", "6,1");
        assertThat(g.play("2,1")).isFalse();
        assertThat(g.play("nonsense")).isFalse();
        String off = g.hint().equals("4,1") ? "6,1" : "4,1";
        assertThat(g.play(off)).isTrue();
        assertThat(g.pegs()).isEqualTo(13);
        assertThat(g.legalMoves()).contains(g.hint());
        assertThatThrownBy(() -> new PegBoardGame(6, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new PegBoardGame(4, 10)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void lockPegsHintsOpenEveryLockWithinFiveTries() {
        for (int secret = 0; secret < 1296; secret += 7) {
            LockPegsGame g = new LockPegsGame(secret);
            ArkCabinet.autoplay(g);
            assertThat(g.winner()).as("code %s", LockPegsGame.encode(secret)).isEqualTo(1);
            assertThat(g.tries()).isBetween(1, 5);
            assertThat(g.render()).contains("the lock opens!");
        }
        LockPegsGame g = new LockPegsGame();
        assertThat(g.hint()).isEqualTo("1122");
        assertThat(LockPegsGame.seeded(42L).over()).isFalse();
    }

    @Test
    void lockPegsScoresMatchBruteForceAndCodesRoundTrip() {
        SplittableRandom rnd = new SplittableRandom(362L);
        for (int k = 0; k < 400; k++) {
            int s = rnd.nextInt(1296);
            int t = rnd.nextInt(1296);
            LockPegsGame g = new LockPegsGame(s);
            int before = g.candidatesLeft();
            assertThat(g.play(LockPegsGame.encode(t))).isTrue();
            assertThat(g.candidatesLeft()).isBetween(1, before);
            int bs = bruteScore(s, t);
            assertThat(g.render()).startsWith(LockPegsGame.encode(t) + "  " + bs / 10 + " right place, " + bs % 10);
            assertThat(LockPegsGame.decode(LockPegsGame.encode(s))).isEqualTo(s);
        }
        LockPegsGame g = new LockPegsGame(LockPegsGame.decode("6666"));
        assertThat(g.play("1237")).isFalse();
        assertThat(g.play("123")).isFalse();
        for (int i = 0; i < LockPegsGame.MAX_TRIES; i++) {
            assertThat(g.play("1111")).isTrue();
        }
        assertThat(g.over()).isTrue();
        assertThat(g.winner()).isZero();
        assertThat(g.render()).contains("jams; code 6666");
        assertThat(g.play("6666")).isFalse();
        assertThatThrownBy(() -> new LockPegsGame(1296)).isInstanceOf(IllegalArgumentException.class);
    }
}