// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class BoardingLadderTest {

    /** Forward brute force: can any boarder reach row k? */
    private static boolean reaches(Set<List<Integer>> pegs, int k) {
        for (List<Integer> p : pegs) {
            if (p.get(1) >= k) {
                return true;
            }
        }
        int[][] dirs = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
        for (List<Integer> p : new ArrayList<>(pegs)) {
            for (int[] d : dirs) {
                List<Integer> b = List.of(p.get(0) + d[0], p.get(1) + d[1]);
                List<Integer> c = List.of(p.get(0) + 2 * d[0], p.get(1) + 2 * d[1]);
                if (pegs.contains(b) && !pegs.contains(c)) {
                    Set<List<Integer>> nx = new HashSet<>(pegs);
                    nx.remove(p);
                    nx.remove(b);
                    nx.add(c);
                    if (reaches(nx, k)) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    @Test
    void fewestBoardersPerRow() {
        assertThat(BoardingLadder.fewest(0)).isEqualTo(1);
        assertThat(BoardingLadder.fewest(1)).isEqualTo(2);
        assertThat(BoardingLadder.fewest(2)).isEqualTo(4);
        assertThat(BoardingLadder.fewest(3)).isEqualTo(8);
    }

    @Test
    void layoutsReplayToTheTarget() {
        for (int k = 0; k <= 3; k++) {
            int[][] start = BoardingLadder.layout(k);
            assertThat(start.length).isEqualTo(BoardingLadder.fewest(k));
            for (int[] p : start) {
                assertThat(p[1]).isLessThanOrEqualTo(0);
            }
            int[][] end = BoardingLadder.play(start, BoardingLadder.jumps(k));
            assertThat(end.length).isEqualTo(1);
            assertThat(end[0]).containsExactly(0, k);
        }
        assertThat(BoardingLadder.play(new int[][] {{0, 0}}, new int[][] {{0, 0, 0, 1}})).isEmpty();
    }

    @Test
    void fewerBoardersFailByBruteForce() {
        List<List<Integer>> cells = new ArrayList<>();
        for (int x = -3; x <= 3; x++) {
            for (int y = -3; y <= 0; y++) {
                cells.add(List.of(x, y));
            }
        }
        assertThat(reaches(Set.of(List.of(0, 0)), 1)).isFalse();
        for (int i = 0; i < cells.size(); i++) {
            for (int j = i + 1; j < cells.size(); j++) {
                for (int l = j + 1; l < cells.size(); l++) {
                    assertThat(reaches(new HashSet<>(List.of(cells.get(i), cells.get(j), cells.get(l))), 2)).isFalse();
                }
            }
        }
        Set<List<Integer>> four = new HashSet<>();
        for (int[] p : BoardingLadder.layout(2)) {
            four.add(List.of(p[0], p[1]));
        }
        assertThat(reaches(four, 2)).isTrue();
    }

    @Test
    void pagodaNeverRises() {
        SplittableRandom rnd = new SplittableRandom(423);
        for (int t = 0; t < 300; t++) {
            Set<List<Integer>> pegs = new HashSet<>();
            for (int i = 0; i < 12; i++) {
                pegs.add(List.of(rnd.nextInt(7) - 3, -rnd.nextInt(4)));
            }
            int[][] start = pegs.stream().map(q -> new int[] {q.get(0), q.get(1)}).toArray(int[][]::new);
            int[][] dirs = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
            int[] p = start[rnd.nextInt(start.length)];
            int[] d = dirs[rnd.nextInt(4)];
            int[][] after = BoardingLadder.play(start, new int[][] {{p[0], p[1], d[0], d[1]}});
            if (after.length > 0) {
                assertThat(BoardingLadder.pagoda(after, 3)).isLessThanOrEqualTo(BoardingLadder.pagoda(start, 3) + 1e-12);
            }
        }
    }

    @Test
    void questAndBounds() {
        assertThat(BoardingLadder.quest(2, 4)).isTrue();
        assertThat(BoardingLadder.quest(2, 3)).isFalse();
        assertThat(BoardingLadder.QUEST_ID).isEqualTo("q_boarding_ladder");
        assertThatThrownBy(() -> BoardingLadder.fewest(4)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BoardingLadder.layout(-1)).isInstanceOf(IllegalArgumentException.class);
    }
}