// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.ark.CaskStack.Move;

import java.util.ArrayList;
import java.util.List;

import org.junit.jupiter.api.Test;

class CaskStackTest {

    @Test
    void closedFormMovesMatchTheRecursiveSolution() {
        for (int n = 1; n <= 12; n++) {
            List<Move> rec = new ArrayList<>();
            solve(n - 1, CaskStack.BOW, CaskStack.STERN, CaskStack.MIDSHIPS, rec);
            assertThat((long) rec.size()).isEqualTo(CaskStack.fewestMoves(n));
            for (int m = 1; m <= rec.size(); m++) {
                assertThat(CaskStack.move(n, m)).as("n=%d m=%d", n, m).isEqualTo(rec.get(m - 1));
            }
        }
    }

    @Test
    void deckAfterMatchesReplay() {
        for (int n = 1; n <= 10; n++) {
            int[] spot = new int[n];
            assertThat(CaskStack.deckAfter(n, 0)).containsExactly(spot);
            for (long m = 1; m <= CaskStack.fewestMoves(n); m++) {
                Move mv = CaskStack.move(n, m);
                assertThat(spot[mv.cask()]).isEqualTo(mv.from());
                spot[mv.cask()] = mv.to();
                assertThat(CaskStack.deckAfter(n, m)).as("n=%d m=%d", n, m).containsExactly(spot);
            }
            for (int s : spot) {
                assertThat(s).isEqualTo(CaskStack.STERN);
            }
        }
    }

    @Test
    void optimalLogPassesTheQuestAndBadLogsFail() {
        List<int[]> log = new ArrayList<>();
        for (long m = 1; m <= CaskStack.fewestMoves(5); m++) {
            Move mv = CaskStack.move(5, m);
            log.add(new int[] {mv.from(), mv.to()});
        }
        assertThat(CaskStack.quest(5, log)).isTrue();
        List<int[]> illegal = List.of(new int[] {0, 1}, new int[] {0, 1});
        assertThat(CaskStack.validLog(2, illegal)).isFalse();
        List<int[]> slow = List.of(new int[] {0, 1}, new int[] {1, 2}, new int[] {0, 1},
                new int[] {2, 1}, new int[] {1, 0}, new int[] {1, 2}, new int[] {0, 2});
        assertThat(CaskStack.validLog(2, slow)).isTrue();
        assertThat(CaskStack.quest(2, slow)).isFalse();
        assertThat(CaskStack.quest(1, List.of(new int[] {0, 2}))).isTrue();
        assertThat(CaskStack.quest(1, List.of(new int[] {0, 1}))).isFalse();
        assertThat(CaskStack.QUEST_ID).isEqualTo("q_cask_stack");
    }

    @Test
    void bigStacksAndValidation() {
        assertThat(CaskStack.fewestMoves(60)).isEqualTo((1L << 60) - 1);
        assertThat(CaskStack.move(60, 1L << 59).cask()).isEqualTo(59);
        assertThat(CaskStack.deckAfter(60, CaskStack.fewestMoves(60))).containsOnly(CaskStack.STERN);
        assertThatThrownBy(() -> CaskStack.move(3, 8)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CaskStack.fewestMoves(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CaskStack.deckAfter(3, -1)).isInstanceOf(IllegalArgumentException.class);
    }

    private static void solve(int cask, int from, int to, int via, List<Move> out) {
        if (cask < 0) {
            return;
        }
        solve(cask - 1, from, via, to, out);
        out.add(new Move(cask, from, to));
        solve(cask - 1, via, to, from, out);
    }
}
