// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.Arrays;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class ChainLinksTest {

    private static final ChainLinks.Kind U = ChainLinks.Kind.UNSIGNED;
    private static final ChainLinks.Kind S = ChainLinks.Kind.SIGNED;

    private static BigInteger unsigned(long v) {
        return new BigInteger(Long.toUnsignedString(v));
    }

    private static BigInteger value(byte[] c, boolean signed) {
        BigInteger r = BigInteger.ZERO;
        for (int i = c.length - 1; i >= 0; i--) {
            r = r.shiftLeft(7).or(BigInteger.valueOf(c[i] & 0x7F));
        }
        if (signed && (c[c.length - 1] & 0x40) != 0) {
            r = r.subtract(BigInteger.ONE.shiftLeft(7 * c.length));
        }
        return r;
    }

    @Test
    void roundTripsAgainstBigInteger() {
        SplittableRandom r = new SplittableRandom(413);
        long[] vs = new long[600];
        for (int i = 0; i < vs.length; i++) {
            vs[i] = r.nextLong() >> r.nextInt(64);
        }
        vs[0] = Long.MIN_VALUE;
        vs[1] = Long.MAX_VALUE;
        vs[2] = 0;
        vs[3] = -1;
        for (long v : vs) {
            byte[] u = ChainLinks.encode(U, v);
            byte[] s = ChainLinks.encode(S, v);
            assertThat(value(u, false)).isEqualTo(unsigned(v));
            assertThat(value(s, true)).isEqualTo(BigInteger.valueOf(v));
            assertThat(u).hasSize(ChainLinks.length(U, v));
            assertThat(s).hasSize(ChainLinks.length(S, v));
        }
        assertThat(ChainLinks.decodeAll(U, ChainLinks.encodeAll(U, vs))).containsExactly(vs);
        assertThat(ChainLinks.decodeAll(S, ChainLinks.encodeAll(S, vs))).containsExactly(vs);
    }

    @Test
    void specVectorsAndRejections() {
        assertThat(ChainLinks.encode(U, 624_485)).containsExactly(0xE5, 0x8E, 0x26);
        assertThat(ChainLinks.encode(S, -123_456)).containsExactly(0xC0, 0xBB, 0x78);
        assertThat(ChainLinks.encode(U, 127)).containsExactly(0x7F);
        assertThat(ChainLinks.encode(S, 63)).containsExactly(0x3F);
        assertThat(ChainLinks.encode(S, 64)).containsExactly(0xC0, 0x00);
        assertThat(ChainLinks.encode(S, -64)).containsExactly(0x40);
        assertThat(ChainLinks.encode(U, -1L)).hasSize(10);
        assertThatThrownBy(() -> ChainLinks.decodeAll(U, new byte[] {(byte) 0x80}))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ChainLinks.decodeAll(U, new byte[] {(byte) 0x81, 0x00}))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ChainLinks.decodeAll(S, new byte[] {(byte) 0xFF, 0x7F}))
            .isInstanceOf(IllegalArgumentException.class);
        byte[] over = new byte[10];
        Arrays.fill(over, (byte) 0xFF);
        over[9] = 0x02;
        assertThatThrownBy(() -> ChainLinks.decodeAll(U, over)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void grades() {
        byte[] d = ChainLinks.encodeAll(S, 5, -300, 1L << 40);
        assertThat(ChainLinks.grade(S, d, new long[] {5, -300, 1L << 40})).isEqualTo(ChainLinks.Grade.LINKED);
        assertThat(ChainLinks.grade(S, new byte[] {(byte) 0x80}, new long[] {0})).isEqualTo(ChainLinks.Grade.SNAPPED);
        assertThat(ChainLinks.forgemasterLine(ChainLinks.Grade.LINKED)).contains("Forgemaster");
        assertThat(ChainLinks.forgemasterLine(ChainLinks.Grade.SNAPPED)).contains("snapped");
        assertThat(ChainLinks.QUEST_ID).isEqualTo("q_chain_links");
    }
}
