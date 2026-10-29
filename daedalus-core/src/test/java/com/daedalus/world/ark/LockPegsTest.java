// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class LockPegsTest {

    private static int bruteScore(int s, int g) {
        int[] a = new int[4];
        int[] b = new int[4];
        for (int i = 0; i < 4; i++) {
            a[i] = LockPegs.peg(s, i);
            b[i] = LockPegs.peg(g, i);
        }
        int black = 0;
        boolean[] usedA = new boolean[4];
        boolean[] usedB = new boolean[4];
        for (int i = 0; i < 4; i++) {
            if (a[i] == b[i]) {
                black++;
                usedA[i] = true;
                usedB[i] = true;
            }
        }
        int white = 0;
        for (int i = 0; i < 4; i++) {
            for (int j = 0; !usedB[i] && j < 4; j++) {
                if (!usedA[j] && a[j] == b[i]) {
                    usedA[j] = true;
                    usedB[i] = true;
                    white++;
                }
            }
        }
        return black * 10 + white;
    }

    @Test
    void scoreMatchesBruteForceForAllPairs() {
        for (int s = 0; s < LockPegs.CODES; s++) {
            for (int g = 0; g < LockPegs.CODES; g += 7) {
                assertThat(LockPegs.score(s, g)).isEqualTo(bruteScore(s, g));
            }
        }
    }

    @Test
    void knuthOpensSampledLocksWithinFive() {
        SplittableRandom rnd = new SplittableRandom(362);
        int max = 0;
        for (int t = 0; t < 120; t++) {
            int tries = LockPegs.solve(rnd.nextInt(LockPegs.CODES));
            max = Math.max(max, tries);
        }
        assertThat(max).isLessThanOrEqualTo(5);
        assertThat(LockPegs.filter(new int[] {0, 1, 2}, 0, 40)).containsExactly(0);
    }

    @Test
    void questAndGuards() {
        assertThat(LockPegs.QUEST_ID).isEqualTo("q_lock_pegs");
        assertThat(LockPegs.quest(0, 0, 40)).isTrue();
        assertThat(LockPegs.quest(1, 6, 22)).isTrue();
        assertThat(LockPegs.quest(1, 6, 11)).isFalse();
        assertThatThrownBy(() -> LockPegs.score(1296, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}