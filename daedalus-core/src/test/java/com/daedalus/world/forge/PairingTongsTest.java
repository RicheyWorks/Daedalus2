// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class PairingTongsTest {

    @Test
    void matchesEnumerationOrder() {
        long z = 0;
        for (long d = 0; d < 300; d++) {
            for (long y = 0; y <= d; y++) {
                long x = d - y;
                assertThat(PairingTongs.cantor(x, y)).isEqualTo(z);
                assertThat(PairingTongs.uncantor(z)).isEqualTo(new PairingTongs.Pair(x, y));
                z++;
            }
        }
        long w = 0;
        for (long s = 0; s < 300; s++) {
            for (long x = 0; x < s; x++) {
                assertThat(PairingTongs.szudzik(x, s)).isEqualTo(w);
                assertThat(PairingTongs.unszudzik(w++)).isEqualTo(new PairingTongs.Pair(x, s));
            }
            for (long y = 0; y <= s; y++) {
                assertThat(PairingTongs.szudzik(s, y)).isEqualTo(w);
                assertThat(PairingTongs.unszudzik(w++)).isEqualTo(new PairingTongs.Pair(s, y));
            }
        }
    }

    @Test
    void knownValuesAndLargeIds() {
        assertThat(PairingTongs.cantor(47, 32)).isEqualTo(3192);
        assertThat(PairingTongs.szudzik(3, 5)).isEqualTo(28);
        SplittableRandom r = new SplittableRandom(421);
        for (int t = 0; t < 500; t++) {
            long x = r.nextLong(2_000_000_000L);
            long y = r.nextLong(2_000_000_000L);
            assertThat(PairingTongs.uncantor(PairingTongs.cantor(x, y))).isEqualTo(new PairingTongs.Pair(x, y));
            assertThat(PairingTongs.unszudzik(PairingTongs.szudzik(x, y))).isEqualTo(new PairingTongs.Pair(x, y));
        }
        for (int t = 0; t < 500; t++) {
            long z = r.nextLong(Long.MAX_VALUE);
            PairingTongs.Pair c = PairingTongs.uncantor(z);
            assertThat(PairingTongs.cantor(c.x(), c.y())).isEqualTo(z);
            PairingTongs.Pair s = PairingTongs.unszudzik(z);
            assertThat(PairingTongs.szudzik(s.x(), s.y())).isEqualTo(z);
        }
        PairingTongs.Pair top = PairingTongs.uncantor(Long.MAX_VALUE);
        assertThat(PairingTongs.cantor(top.x(), top.y())).isEqualTo(Long.MAX_VALUE);
        assertThatThrownBy(() -> PairingTongs.cantor(Long.MAX_VALUE / 2, Long.MAX_VALUE / 2))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PairingTongs.szudzik(-1, 0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void grades() {
        assertThat(PairingTongs.grade(47, 32, 3192)).isEqualTo(PairingTongs.Grade.GRIPPED);
        assertThat(PairingTongs.grade(47, 32, 3193)).isEqualTo(PairingTongs.Grade.DROPPED);
        assertThat(PairingTongs.forgemasterLine(PairingTongs.Grade.GRIPPED)).contains("Forgemaster");
        assertThat(PairingTongs.forgemasterLine(PairingTongs.Grade.DROPPED)).contains("dropped");
        assertThat(PairingTongs.QUEST_ID).isEqualTo("q_pairing_tongs");
    }
}
