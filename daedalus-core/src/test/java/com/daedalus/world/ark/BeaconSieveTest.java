// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class BeaconSieveTest {

    @Test
    void knownCountsAndBeacons() {
        assertThat(BeaconSieve.primesUpTo(30)).containsExactly(2, 3, 5, 7, 11, 13, 17, 19, 23, 29);
        assertThat(BeaconSieve.count(0)).isZero();
        assertThat(BeaconSieve.count(1)).isZero();
        assertThat(BeaconSieve.count(2)).isEqualTo(1);
        assertThat(BeaconSieve.count(100)).isEqualTo(25);
        assertThat(BeaconSieve.count(1_000_000)).isEqualTo(78_498);
        assertThat(BeaconSieve.kth(1)).isEqualTo(2);
        assertThat(BeaconSieve.kth(5)).isEqualTo(11);
        assertThat(BeaconSieve.kth(6)).isEqualTo(13);
        assertThat(BeaconSieve.kth(10_000)).isEqualTo(104_729);
    }

    @Test
    void sieveMatchesTrialDivision() {
        boolean[] c = BeaconSieve.composite(5000);
        for (int i = 0; i <= 5000; i++) {
            assertThat(!c[i]).as("i=%d", i).isEqualTo(BeaconSieve.isPrime(i));
        }
        for (int k = 1; k <= 700; k++) {
            assertThat(BeaconSieve.isPrime(BeaconSieve.kth(k))).isTrue();
            assertThat(BeaconSieve.count(BeaconSieve.kth(k))).isEqualTo(k);
        }
    }

    @Test
    void segmentMatchesTrialDivision() {
        assertThat(BeaconSieve.segment(0, 20)).containsExactly(2, 3, 5, 7, 11, 13, 17, 19);
        assertThat(BeaconSieve.segment(1_000_000_000_000L - 100, 1_000_000_000_000L))
            .containsExactly(999_999_999_937L, 999_999_999_959L, 999_999_999_961L, 999_999_999_989L);
        SplittableRandom rnd = new SplittableRandom(246);
        for (int t = 0; t < 40; t++) {
            long lo = rnd.nextLong(0, 2_000_000_000L);
            long hi = lo + rnd.nextInt(300);
            long[] got = BeaconSieve.segment(lo, hi);
            int k = 0;
            for (long x = lo; x <= hi; x++) {
                if (BeaconSieve.isPrime(x)) {
                    assertThat(got[k++]).isEqualTo(x);
                }
            }
            assertThat(got).hasSize(k);
        }
    }

    @Test
    void questAndBounds() {
        assertThat(BeaconSieve.quest(100, 541)).isTrue();
        assertThat(BeaconSieve.quest(100, 547)).isFalse();
        assertThat(BeaconSieve.QUEST_ID).isEqualTo("q_beacon_sieve");
        assertThatThrownBy(() -> BeaconSieve.kth(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BeaconSieve.segment(5, 4)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BeaconSieve.primesUpTo(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThat(BeaconSieve.segment(0, 1)).isEmpty();
    }
}
