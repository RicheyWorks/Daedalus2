// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;
import java.util.SplittableRandom;
import java.util.zip.Adler32;
import org.junit.jupiter.api.Test;

class TallySumsTest {

    private static byte[] ascii(String s) {
        return s.getBytes(StandardCharsets.US_ASCII);
    }

    @Test
    void matchesJdkAndRolling() {
        SplittableRandom r = new SplittableRandom(405);
        for (int t = 0; t < 200; t++) {
            byte[] d = new byte[r.nextInt(t < 190 ? 300 : 40_000)];
            r.nextBytes(d);
            Adler32 jdk = new Adler32();
            jdk.update(d);
            assertThat(TallySums.adler32(d)).isEqualTo(jdk.getValue());
        }
        byte[] s = new byte[2000];
        r.nextBytes(s);
        int n = 64;
        long h = TallySums.adler32(s, 0, n);
        for (int i = 1; i + n <= s.length; i++) {
            h = TallySums.roll(h, n, s[i - 1], s[i + n - 1]);
            assertThat(h).isEqualTo(TallySums.adler32(s, i, n));
        }
    }

    @Test
    void publishedVectors() {
        assertThat(TallySums.adler32(ascii("Wikipedia"))).isEqualTo(0x11E60398L);
        assertThat(TallySums.adler32(new byte[0])).isEqualTo(1L);
        assertThat(TallySums.fletcher16(ascii("abcde"))).isEqualTo(0xC8F0);
        assertThat(TallySums.fletcher16(ascii("abcdef"))).isEqualTo(0x2057);
        assertThat(TallySums.fletcher32(ascii("abcde"))).isEqualTo(0xF04FC729L);
        assertThat(TallySums.fletcher32(ascii("abcdef"))).isEqualTo(0x56502D2AL);
    }

    @Test
    void grades() {
        byte[] d = ascii("iron ingots x12");
        long a = TallySums.adler32(d);
        assertThat(TallySums.grade(d, a)).isEqualTo(TallySums.Grade.TALLIED);
        assertThat(TallySums.grade(ascii("iron ingots x13"), a)).isEqualTo(TallySums.Grade.SHORT);
        assertThat(TallySums.forgemasterLine(TallySums.Grade.TALLIED)).contains("Forgemaster");
        assertThat(TallySums.forgemasterLine(TallySums.Grade.SHORT)).contains("short");
        assertThat(TallySums.QUEST_ID).isEqualTo("q_tally_sums");
    }
}
