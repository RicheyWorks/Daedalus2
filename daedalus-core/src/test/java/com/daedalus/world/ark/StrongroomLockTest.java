// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class StrongroomLockTest {

    @Test
    void everyWindowAppearsExactlyOnceCyclically() {
        for (int k = 1; k <= 5; k++) {
            for (int n = 1; n <= 6; n++) {
                if (Math.pow(k, n) > 20_000) {
                    continue;
                }
                int[] c = StrongroomLock.cyclic(k, n);
                int total = StrongroomLock.codes(k, n);
                assertThat(c).hasSize(total);
                int[] hits = new int[total];
                for (int s = 0; s < total; s++) {
                    int code = 0;
                    for (int j = 0; j < n; j++) {
                        code = code * k + c[(s + j) % total];
                    }
                    hits[code]++;
                }
                assertThat(hits).as("k=%d n=%d", k, n).containsOnly(1);
            }
        }
    }

    @Test
    void keySequencePassesTheQuestAtMinimumLength() {
        for (int k = 2; k <= 4; k++) {
            for (int n = 1; n <= 5; n++) {
                int[] key = StrongroomLock.keySequence(k, n);
                assertThat(key).hasSize(StrongroomLock.codes(k, n) + n - 1);
                assertThat(StrongroomLock.quest(k, n, key)).as("k=%d n=%d", k, n).isTrue();
            }
        }
    }

    @Test
    void knownSequenceAndNaiveIsLonger() {
        assertThat(StrongroomLock.cyclic(2, 3)).containsExactly(0, 0, 0, 1, 0, 1, 1, 1);
        assertThat(StrongroomLock.cyclic(10, 4)).hasSize(10_000);
        int[] naive = new int[3 * 8];
        for (int code = 0; code < 8; code++) {
            naive[3 * code] = (code >> 2) & 1;
            naive[3 * code + 1] = (code >> 1) & 1;
            naive[3 * code + 2] = code & 1;
        }
        assertThat(StrongroomLock.triesEveryCode(2, 3, naive)).isTrue();
        assertThat(StrongroomLock.quest(2, 3, naive)).isFalse();
    }

    @Test
    void badKeysAndValidation() {
        assertThat(StrongroomLock.triesEveryCode(2, 2, new int[] {0, 0, 1, 0})).isFalse();
        assertThat(StrongroomLock.triesEveryCode(2, 2, new int[] {0, 2, 1})).isFalse();
        assertThat(StrongroomLock.QUEST_ID).isEqualTo("q_strongroom_lock");
        assertThatThrownBy(() -> StrongroomLock.codes(0, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> StrongroomLock.codes(10, 8)).isInstanceOf(IllegalArgumentException.class);
    }
}
