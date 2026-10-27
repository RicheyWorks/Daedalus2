// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.HashMap;
import java.util.Map;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class FigureheadNumeralsTest {

    private static final String[][] PLACES = {
        {"", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"},
        {"", "X", "XX", "XXX", "XL", "L", "LX", "LXX", "LXXX", "XC"},
        {"", "C", "CC", "CCC", "CD", "D", "DC", "DCC", "DCCC", "CM"},
        {"", "M", "MM", "MMM"}};

    private static String table(int n) {
        return PLACES[3][n / 1000] + PLACES[2][n / 100 % 10] + PLACES[1][n / 10 % 10] + PLACES[0][n % 10];
    }

    @Test
    void everyNumberMatchesPlaceTable() {
        for (int n = 1; n <= 3999; n++) {
            String r = table(n);
            assertThat(FigureheadNumerals.carve(n)).isEqualTo(r);
            assertThat(FigureheadNumerals.read(r)).hasValue(n);
        }
    }

    @Test
    void randomStringsReadOnlyWhenCanonical() {
        Map<String, Integer> canon = new HashMap<>();
        for (int n = 1; n <= 3999; n++) {
            canon.put(table(n), n);
        }
        String letters = "IVXLCDM";
        SplittableRandom rnd = new SplittableRandom(325);
        int hits = 0;
        for (int t = 0; t < 200_000; t++) {
            StringBuilder sb = new StringBuilder();
            int len = rnd.nextInt(1, 7);
            for (int i = 0; i < len; i++) {
                sb.append(letters.charAt(rnd.nextInt(letters.length())));
            }
            String s = sb.toString();
            Integer want = canon.get(s);
            if (want == null) {
                assertThat(FigureheadNumerals.read(s)).isEmpty();
            } else {
                hits++;
                assertThat(FigureheadNumerals.read(s)).hasValue(want);
            }
        }
        assertThat(hits).isPositive();
    }

    @Test
    void questAndGuards() {
        assertThat(FigureheadNumerals.QUEST_ID).isEqualTo("q_figurehead_numerals");
        assertThat(FigureheadNumerals.quest(1994, "MCMXCIV")).isTrue();
        assertThat(FigureheadNumerals.quest(4, "IIII")).isFalse();
        assertThat(FigureheadNumerals.read("IC")).isEmpty();
        assertThat(FigureheadNumerals.read("VX")).isEmpty();
        assertThat(FigureheadNumerals.read("MMMM")).isEmpty();
        assertThat(FigureheadNumerals.read("")).isEmpty();
        assertThatThrownBy(() -> FigureheadNumerals.carve(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FigureheadNumerals.carve(4000)).isInstanceOf(IllegalArgumentException.class);
    }
}