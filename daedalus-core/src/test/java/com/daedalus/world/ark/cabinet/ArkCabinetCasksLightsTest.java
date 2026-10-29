// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.ark.DeckLights;
import java.util.ArrayDeque;
import java.util.HashSet;
import java.util.Set;
import org.junit.jupiter.api.Test;

class ArkCabinetCasksLightsTest {

    private static final int O = DeckLights.OPEN;
    private static final int W = DeckLights.WALL;

    /** Brute force BFS over (A, B) levels: fewest moves until one cask holds c, or -1. */
    private static int bfs(int a, int b, int c) {
        ArrayDeque<int[]> q = new ArrayDeque<>();
        Set<Integer> seen = new HashSet<>();
        q.add(new int[] {0, 0, 0});
        seen.add(0);
        while (!q.isEmpty()) {
            int[] s = q.poll();
            int x = s[0];
            int y = s[1];
            if (x == c || y == c) {
                return s[2];
            }
            int ab = Math.min(x, b - y);
            int ba = Math.min(y, a - x);
            int[][] next = {{a, y}, {x, b}, {0, y}, {x, 0}, {x - ab, y + ab}, {x + ba, y - ba}};
            for (int[] n : next) {
                if (seen.add(n[0] * 1000 + n[1])) {
                    q.add(new int[] {n[0], n[1], s[2] + 1});
                }
            }
        }
        return -1;
    }

    /** Independent Akari check used to brute force small decks. */
    private static boolean akari(int[][] g, int[][] l) {
        int h = g.length;
        int w = g[0].length;
        int[][] dirs = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
        for (int r = 0; r < h; r++) {
            for (int c = 0; c < w; c++) {
                if (g[r][c] >= 0) {
                    int n = 0;
                    for (int[] d : dirs) {
                        int rr = r + d[0];
                        int cc = c + d[1];
                        if (rr >= 0 && rr < h && cc >= 0 && cc < w && l[rr][cc] == 1) {
                            n++;
                        }
                    }
                    if (n != g[r][c]) {
                        return false;
                    }
                    continue;
                }
                if (g[r][c] != O) {
                    continue;
                }
                boolean lit = l[r][c] == 1;
                for (int[] d : dirs) {
                    for (int rr = r + d[0], cc = c + d[1]; rr >= 0 && rr < h && cc >= 0 && cc < w
                        && g[rr][cc] == O; rr += d[0], cc += d[1]) {
                        if (l[rr][cc] == 1) {
                            if (l[r][c] == 1) {
                                return false;
                            }
                            lit = true;
                        }
                    }
                }
                if (!lit) {
                    return false;
                }
            }
        }
        return true;
    }

    private static long bruteCount(int[][] g) {
        int h = g.length;
        int w = g[0].length;
        long count = 0;
        for (int mask = 0; mask < 1 << (h * w); mask++) {
            int[][] l = new int[h][w];
            boolean ok = true;
            for (int i = 0; i < h * w && ok; i++) {
                if ((mask >> i & 1) == 1) {
                    ok = g[i / w][i % w] == O;
                    l[i / w][i % w] = 1;
                }
            }
            if (ok && akari(g, l)) {
                count++;
            }
        }
        return count;
    }

    @Test
    void casksAutoplayIsFewestMovesByBfs() {
        for (int a = 1; a <= 9; a++) {
            for (int b = 1; b <= 9; b++) {
                for (int c = 1; c <= Math.max(a, b); c++) {
                    int best = bfs(a, b, c);
                    if (best < 0) {
                        int fa = a;
                        int fb = b;
                        int fc = c;
                        assertThatThrownBy(() -> new MeasuringCasksGame(fa, fb, fc))
                            .isInstanceOf(IllegalArgumentException.class);
                        continue;
                    }
                    MeasuringCasksGame g = new MeasuringCasksGame(a, b, c);
                    assertThat(g.fewest()).as("%d %d %d", a, b, c).isEqualTo(best);
                    assertThat(ArkCabinet.autoplay(g)).hasSize(best);
                    assertThat(g.winner()).isEqualTo(1);
                }
            }
        }
    }

    @Test
    void casksHintRecoversAfterAWrongMove() {
        MeasuringCasksGame g = new MeasuringCasksGame();
        assertThat(g.legalMoves()).containsExactly("fillA", "fillB");
        assertThat(g.play("emptyA")).isFalse();
        assertThat(g.play("bogus")).isFalse();
        String first = g.hint();
        assertThat(g.play(first.equals("fillA") ? "fillB" : "fillA")).isTrue();
        assertThat(g.render()).contains("moves 1");
        ArkCabinet.autoplay(g);
        assertThat(g.over()).isTrue();
        assertThat(g.levelA() == 4 || g.levelB() == 4).isTrue();
        assertThat(g.render()).contains("measured 4 litres");
        assertThat(g.play("fillA")).isFalse();
    }

    @Test
    void deckLightsSolvableDecksMatchBruteForce() {
        int[][][] decks = {
            {{O, O, O}, {O, W, O}, {O, O, O}},
            {{O, O, O}, {O, 4, O}, {O, O, O}},
            {{O, 1, O}, {O, O, O}, {W, O, 0}},
            {{O, O}, {O, O}},
            {{O, O, O, O}, {O, 2, O, O}, {O, O, W, O}, {O, O, O, O}},
        };
        for (int[][] d : decks) {
            long brute = bruteCount(d);
            assertThat(DeckLights.count(d, 1_000_000)).isEqualTo(brute);
            if (brute == 0) {
                assertThatThrownBy(() -> new DeckLightsGame(d)).isInstanceOf(IllegalArgumentException.class);
                continue;
            }
            DeckLightsGame g = new DeckLightsGame(d);
            ArkCabinet.autoplay(g);
            assertThat(g.winner()).isEqualTo(1);
            assertThat(akari(d, g.lampBoard())).isTrue();
        }
    }

    @Test
    void deckLightsRejectsBadMovesAndFinishesStandardDeck() {
        DeckLightsGame g = new DeckLightsGame();
        assertThat(g.play("2,2")).isFalse();
        assertThat(g.play("0,1")).isFalse();
        assertThat(g.play("x,1")).isFalse();
        assertThat(g.play("1,1")).isTrue();
        assertThat(g.lampCount()).isEqualTo(1);
        assertThat(g.play("1,1")).isTrue();
        assertThat(g.toggles()).isEqualTo(2);
        ArkCabinet.autoplay(g);
        assertThat(g.over()).isTrue();
        assertThat(g.render()).contains("deck lit!");
        assertThat(g.hint()).isEmpty();
        assertThatThrownBy(() -> new DeckLightsGame(new int[][] {{1, W}, {W, O}}))
            .isInstanceOf(IllegalArgumentException.class);
    }
}
