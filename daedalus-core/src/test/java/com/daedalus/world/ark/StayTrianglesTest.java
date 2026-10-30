// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class StayTrianglesTest {

    private static long gcd(long x, long y) {
        return y == 0 ? x : gcd(y, x % y);
    }

    private static List<String> brute(long maxP, boolean primitiveOnly) {
        List<String> out = new ArrayList<>();
        for (long c = 1; c <= maxP; c++) {
            for (long a = 1; a < c; a++) {
                long b2 = c * c - a * a;
                long b = (long) Math.sqrt((double) b2);
                while (b * b > b2) {
                    b--;
                }
                while ((b + 1) * (b + 1) <= b2) {
                    b++;
                }
                if (b > a && b * b == b2 && a + b + c <= maxP && (!primitiveOnly || gcd(gcd(a, b), c) == 1)) {
                    out.add(a + "," + b + "," + c);
                }
            }
        }
        return out;
    }

    private static List<String> text(List<long[]> ts) {
        List<String> out = new ArrayList<>();
        for (long[] t : ts) {
            out.add(t[0] + "," + t[1] + "," + t[2]);
        }
        return out;
    }

    @Test
    void primitivesMatchBruteForce() {
        List<String> got = text(StayTriangles.primitives(1500));
        assertThat(got).containsExactlyInAnyOrderElementsOf(brute(1500, true));
        assertThat(got.get(0)).isEqualTo("3,4,5");
        assertThat(StayTriangles.primitives(1_000_000)).hasSize(70_229);
    }

    @Test
    void perimeterAndHypotenuse() {
        List<String> all = brute(1200, false);
        for (long p = 1; p <= 1200; p++) {
            List<String> want = new ArrayList<>();
            for (String s : all) {
                String[] x = s.split(",");
                if (Long.parseLong(x[0]) + Long.parseLong(x[1]) + Long.parseLong(x[2]) == p) {
                    want.add(s);
                }
            }
            assertThat(text(StayTriangles.withPerimeter(p))).as("p=%d", p).containsExactlyInAnyOrderElementsOf(want);
        }
        assertThat(text(StayTriangles.withPerimeter(120))).containsExactly("20,48,52", "24,45,51", "30,40,50");
        assertThat(text(StayTriangles.withHypotenuse(25))).containsExactly("7,24,25", "15,20,25");
        assertThat(StayTriangles.withHypotenuse(7)).isEmpty();
        assertThat(StayTriangles.withHypotenuse(5 * 13 * 17)).hasSize(13);
    }

    @Test
    void questAndBounds() {
        assertThat(StayTriangles.quest(3, 4, 5)).isTrue();
        assertThat(StayTriangles.quest(5, 12, 13)).isTrue();
        assertThat(StayTriangles.quest(5, 12, 14)).isFalse();
        assertThat(StayTriangles.quest(0, 5, 5)).isFalse();
        assertThat(StayTriangles.QUEST_ID).isEqualTo("q_stay_triangles");
        assertThatThrownBy(() -> StayTriangles.primitives(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> StayTriangles.withHypotenuse(0)).isInstanceOf(IllegalArgumentException.class);
    }
}