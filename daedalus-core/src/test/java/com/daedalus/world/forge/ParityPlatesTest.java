// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class ParityPlatesTest {

    @Test
    void exhaustiveFlips() {
        for (int n = 0; n < 16; n++) {
            int w = ParityPlates.encode(n);
            assertThat(ParityPlates.syndrome(w)).isZero();
            assertThat(ParityPlates.decode(w)).isEqualTo(new ParityPlates.Decoded(n, ParityPlates.Status.CLEAN));
            for (int i = 0; i < 8; i++) {
                ParityPlates.Decoded d = ParityPlates.decode(w ^ (1 << i));
                assertThat(d).isEqualTo(new ParityPlates.Decoded(n, ParityPlates.Status.CORRECTED));
                for (int j = i + 1; j < 8; j++) {
                    assertThat(ParityPlates.decode(w ^ (1 << i) ^ (1 << j)).status())
                        .isEqualTo(ParityPlates.Status.DOUBLE);
                }
            }
            for (int m = n + 1; m < 16; m++) {
                int v = ParityPlates.encode(m);
                assertThat(Integer.bitCount(w ^ v)).isGreaterThanOrEqualTo(4);
                assertThat(Integer.bitCount((w ^ v) & 0x7F)).isGreaterThanOrEqualTo(3);
            }
        }
    }

    @Test
    void byteStreams() {
        SplittableRandom r = new SplittableRandom(391);
        byte[] data = new byte[500];
        r.nextBytes(data);
        byte[] plates = ParityPlates.encodeBytes(data);
        for (int i = 0; i < plates.length; i += 3) {
            plates[i] ^= (byte) (1 << r.nextInt(8));
        }
        assertThat(ParityPlates.decodeBytes(plates)).containsExactly(data);
        plates[1] ^= 0x03;
        assertThat(ParityPlates.decode(plates[1] & 0xFF).status()).isEqualTo(ParityPlates.Status.DOUBLE);
        assertThatThrownBy(() -> ParityPlates.decodeBytes(plates)).isInstanceOf(IllegalArgumentException.class);
        assertThat(ParityPlates.encode(0)).isZero();
        assertThat(ParityPlates.encode(15)).isEqualTo(0xFF);
    }

    @Test
    void grades() {
        int w = ParityPlates.encode(9);
        assertThat(ParityPlates.grade(9, ParityPlates.decode(w ^ 4))).isEqualTo(ParityPlates.Grade.MENDED);
        assertThat(ParityPlates.grade(9, ParityPlates.decode(w ^ 6))).isEqualTo(ParityPlates.Grade.GARBLED);
        assertThat(ParityPlates.forgemasterLine(ParityPlates.Grade.MENDED)).contains("Forgemaster");
        assertThat(ParityPlates.forgemasterLine(ParityPlates.Grade.GARBLED)).contains("garbled");
        assertThat(ParityPlates.QUEST_ID).isEqualTo("q_parity_plates");
    }
}
