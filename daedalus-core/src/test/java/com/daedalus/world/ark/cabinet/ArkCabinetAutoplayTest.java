// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.ark.GalleyStack;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class ArkCabinetAutoplayTest {

    /** Brute force: true when the player to move wins Wythoff from (x, y). */
    private static boolean wythoffWins(int x, int y, Map<Integer, Boolean> memo) {
        int key = x * 64 + y;
        Boolean got = memo.get(key);
        if (got != null) {
            return got;
        }
        boolean win = false;
        for (int k = 1; k <= x && !win; k++) {
            win = !wythoffWins(x - k, y, memo);
        }
        for (int k = 1; k <= y && !win; k++) {
            win = !wythoffWins(x, y - k, memo);
        }
        for (int k = 1; k <= Math.min(x, y) && !win; k++) {
            win = !wythoffWins(x - k, y - k, memo);
        }
        memo.put(key, win);
        return win;
    }

    /** Brute force: true when the player to move wins Kayles on these sorted rows. */
    private static boolean kaylesWins(List<Integer> rows, Map<List<Integer>, Boolean> memo) {
        Boolean got = memo.get(rows);
        if (got != null) {
            return got;
        }
        boolean win = false;
        for (int r = 0; r < rows.size() && !win; r++) {
            int len = rows.get(r);
            for (int k = 1; k <= 2 && !win; k++) {
                for (int s = 0; s + k <= len && !win; s++) {
                    List<Integer> next = new ArrayList<>(rows);
                    next.remove(r);
                    if (s > 0) {
                        next.add(s);
                    }
                    if (len - s - k > 0) {
                        next.add(len - s - k);
                    }
                    next.sort(null);
                    win = !kaylesWins(next, memo);
                }
            }
        }
        memo.put(List.copyOf(rows), win);
        return win;
    }

    @Test
    void everyCabinetGameAutoplaysToAnEnd() {
        ArkCabinet cab = ArkCabinet.standard();
        assertThat(cab.slots()).hasSize(17);
        for (ArkCabinet.Slot s : cab.slots()) {
            ArkCabinetGame g = s.open();
            List<String> moves = ArkCabinet.autoplay(g);
            assertThat(g.over()).as(s.id()).isTrue();
            assertThat(moves).as(s.id()).isNotEmpty();
            assertThat(g.winner()).as(s.id()).isBetween(0, 2);
            assertThat(g.toMove()).as(s.id()).isZero();
            assertThat(g.hint()).as(s.id()).isEmpty();
            assertThat(ArkCabinet.quest(g)).as(s.id()).isTrue();
        }
        assertThat(cab.arcadeDescription()).contains("17 crew games");
    }

    @Test
    void twoHoardsPerfectPlayMatchesBruteForce() {
        Map<Integer, Boolean> memo = new HashMap<>();
        for (int x = 0; x <= 12; x++) {
            for (int y = 0; y <= 12; y++) {
                if (x + y == 0) {
                    continue;
                }
                TwoHoardsGame g = new TwoHoardsGame(x, y);
                ArkCabinet.autoplay(g);
                assertThat(g.winner() == 1).as("(%d,%d)", x, y).isEqualTo(wythoffWins(x, y, memo));
            }
        }
        TwoHoardsGame g = new TwoHoardsGame(3, 4);
        assertThat(g.play("3,4")).isFalse();
        assertThat(g.play("4,1")).isFalse();
        assertThat(g.play("3,3")).isTrue();
        assertThat(g.first()).isZero();
        assertThat(g.second()).isEqualTo(1);
        assertThatThrownBy(() -> new TwoHoardsGame(31, 0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void skittleRowPerfectPlayMatchesBruteForce() {
        Map<List<Integer>, Boolean> memo = new HashMap<>();
        int[][] starts = {{1}, {2}, {3}, {4}, {5}, {6}, {7}, {8}, {9}, {1, 1}, {2, 3}, {1, 4}, {3, 5}, {2, 2, 4},
            {1, 2, 3}, {3, 5, 7}};
        for (int[] st : starts) {
            List<Integer> rows = new ArrayList<>();
            for (int n : st) {
                rows.add(n);
            }
            rows.sort(null);
            SkittleRowGame g = new SkittleRowGame(st);
            boolean wins = kaylesWins(rows, memo);
            assertThat(g.moverWins()).isEqualTo(wins);
            ArkCabinet.autoplay(g);
            assertThat(g.winner() == 1).as("rows %s", rows).isEqualTo(wins);
        }
        SkittleRowGame g = new SkittleRowGame(5);
        assertThat(g.play("1,5,2")).isFalse();
        assertThat(g.play("1,2,3")).isFalse();
        assertThat(g.play("1,2,2")).isTrue();
        assertThat(g.rows()).containsExactly(1, 2);
        assertThatThrownBy(() -> new SkittleRowGame(0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void galleyStackSolvesInFewestFlips() {
        GalleyStackGame g = new GalleyStackGame();
        int fewest = g.fewestLeft();
        assertThat(fewest).isBetween(1, GalleyStack.pancakeNumber(6));
        assertThat(ArkCabinet.autoplay(g)).hasSize(fewest);
        assertThat(g.flips()).isEqualTo(fewest);
        assertThat(g.render()).contains("stacked!");
        GalleyStackGame h = new GalleyStackGame(1, 0, 2);
        assertThat(h.play("1")).isFalse();
        assertThat(h.play("4")).isFalse();
        assertThat(h.legalMoves()).containsExactly("2", "3");
        assertThat(h.play("2")).isTrue();
        assertThat(h.over()).isTrue();
        assertThatThrownBy(() -> new GalleyStackGame(0, 1, 2, 3, 4, 5, 6, 7, 8)).isInstanceOf(
            IllegalArgumentException.class);
    }
}