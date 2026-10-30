// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ClampPairs.Grade;
import com.daedalus.world.forge.ClampPairs.Span;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ClampPairsTest {

    private static boolean bruteBalanced(String s) {
        char[] st = new char[s.length()];
        int top = 0;
        for (char c : s.toCharArray()) {
            int o = ClampPairs.OPEN.indexOf(c);
            if (o >= 0) {
                st[top++] = c;
            } else if (top == 0 || ClampPairs.OPEN.indexOf(st[--top]) != ClampPairs.CLOSE.indexOf(c)) {
                return false;
            }
        }
        return top == 0;
    }

    private static int insertDp(String s) {
        int n = s.length();
        int[][] dp = new int[n + 1][n + 1];
        for (int len = 1; len <= n; len++) {
            for (int i = 0; i + len <= n; i++) {
                int j = i + len;
                int best = 1 + dp[i + 1][j];
                if (s.charAt(i) == '(') {
                    for (int k = i + 1; k < j; k++) {
                        if (s.charAt(k) == ')') {
                            best = Math.min(best, dp[i + 1][k] + dp[k + 1][j]);
                        }
                    }
                }
                dp[i][j] = best;
            }
        }
        return dp[0][n];
    }

    @Test
    void longestMatchesBruteForceOnSeededRacks() {
        for (long seed = 0; seed < 300; seed++) {
            String s = ClampPairs.rack(seed, (int) (seed % 30), 1 + (int) (seed % 3));
            int best = 0;
            int bestFrom = 0;
            for (int i = 0; i < s.length(); i++) {
                for (int j = i + 1; j <= s.length(); j++) {
                    if (j - i > best && bruteBalanced(s.substring(i, j))) {
                        best = j - i;
                        bestFrom = i;
                    }
                }
            }
            Span sp = ClampPairs.longestBalanced(s);
            assertThat(sp.length()).as("seed %d %s", seed, s).isEqualTo(best);
            assertThat(sp.from()).as("earliest seed %d", seed).isEqualTo(bestFrom);
            assertThat(ClampPairs.balanced(s)).isEqualTo(bruteBalanced(s));
        }
    }

    @Test
    void insertionsMatchExhaustiveDp() {
        for (long seed = 0; seed < 200; seed++) {
            String s = ClampPairs.rack(seed, (int) (seed % 25), 1);
            assertThat(ClampPairs.insertionsToBalance(s)).as("seed %d %s", seed, s).isEqualTo(insertDp(s));
        }
        assertThat(ClampPairs.insertionsToBalance("())(")).isEqualTo(2);
        assertThatThrownBy(() -> ClampPairs.insertionsToBalance("[")).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void knownRacksGradesLinesAndReplay() {
        assertThat(ClampPairs.longestBalanced("([)]{}()")).isEqualTo(new Span(4, 8));
        assertThat(ClampPairs.longestBalanced(")(")).isEqualTo(new Span(0, 0));
        assertThat(ClampPairs.balanced("{[()]}")).isTrue();
        assertThatThrownBy(() -> ClampPairs.longestBalanced("a")).isInstanceOf(IllegalArgumentException.class);
        assertThat(ClampPairs.grade("(()", new Span(1, 3))).isEqualTo(Grade.LOCKED);
        assertThat(ClampPairs.grade("(()", new Span(0, 2))).isEqualTo(Grade.LOOSE);
        assertThat(ClampPairs.grade("(()", new Span(2, 9))).isEqualTo(Grade.LOOSE);
        for (Grade g : Grade.values()) {
            assertThat(ClampPairs.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(ClampPairs.QUEST_ID).isEqualTo("q_clamp_pairs");
        assertThat(ClampPairs.rack(6, 20, 3)).isEqualTo(ClampPairs.rack(6, 20, 3)).hasSize(20);
        assertThatThrownBy(() -> ClampPairs.rack(1, 2, 4)).isInstanceOf(IllegalArgumentException.class);
    }
}
