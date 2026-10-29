// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class CalkinCoilsTest {

    @Test
    void matchesBreadthFirstTree() {
        int size = 1 << 13;
        long[] num = new long[size];
        long[] den = new long[size];
        num[1] = 1;
        den[1] = 1;
        for (int k = 1; 2 * k + 1 < size; k++) {
            num[2 * k] = num[k];
            den[2 * k] = num[k] + den[k];
            num[2 * k + 1] = num[k] + den[k];
            den[2 * k + 1] = den[k];
        }
        long[] fs = new long[size + 1];
        fs[1] = 1;
        for (int n = 2; n <= size; n++) {
            fs[n] = (n & 1) == 0 ? fs[n / 2] : fs[n / 2] + fs[n / 2 + 1];
        }
        for (int k = 1; k < size; k++) {
            CalkinCoils.Ratio r = CalkinCoils.at(k);
            assertThat(r).isEqualTo(new CalkinCoils.Ratio(num[k], den[k]));
            assertThat(CalkinCoils.indexOf(num[k], den[k])).isEqualTo(k);
            assertThat(CalkinCoils.fusc(k)).isEqualTo(fs[k]);
            assertThat(r.num()).isEqualTo(fs[k]);
            if (k + 1 < size) {
                assertThat(CalkinCoils.next(num[k], den[k])).isEqualTo(new CalkinCoils.Ratio(num[k + 1], den[k + 1]));
            }
        }
        for (long s = 0; s < 300; s++) {
            long k = CalkinCoils.coil(s);
            CalkinCoils.Ratio r = CalkinCoils.at(k);
            assertThat(CalkinCoils.indexOf(r.num(), r.den())).isEqualTo(k);
            assertThat(r.den()).isEqualTo(CalkinCoils.fusc(k + 1));
        }
    }

    @Test
    void knownValues() {
        assertThat(CalkinCoils.at(1)).isEqualTo(new CalkinCoils.Ratio(1, 1));
        assertThat(CalkinCoils.at(2)).isEqualTo(new CalkinCoils.Ratio(1, 2));
        assertThat(CalkinCoils.at(3)).isEqualTo(new CalkinCoils.Ratio(2, 1));
        assertThat(CalkinCoils.at(4)).isEqualTo(new CalkinCoils.Ratio(1, 3));
        assertThat(CalkinCoils.at(10)).isEqualTo(new CalkinCoils.Ratio(3, 5));
        assertThat(CalkinCoils.indexOf(1, 62)).isEqualTo(1L << 61);
        assertThat(CalkinCoils.fusc(0)).isZero();
    }

    @Test
    void grades() {
        assertThat(CalkinCoils.grade(10, 3, 5)).isEqualTo(CalkinCoils.Grade.TRUE);
        assertThat(CalkinCoils.grade(10, 5, 3)).isEqualTo(CalkinCoils.Grade.KINKED);
        assertThat(CalkinCoils.forgemasterLine(CalkinCoils.Grade.TRUE)).contains("Forgemaster");
        assertThat(CalkinCoils.forgemasterLine(CalkinCoils.Grade.KINKED)).contains("kinked");
        assertThat(CalkinCoils.QUEST_ID).isEqualTo("q_calkin_coils");
    }
}
