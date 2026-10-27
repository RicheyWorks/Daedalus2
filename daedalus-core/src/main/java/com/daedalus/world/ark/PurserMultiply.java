// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;

/**
 * G257 The Purser's Long Sum: the ark purser multiplies huge cargo tallies digit by digit.
 * {@link #karatsuba} splits each product into three half-size products instead of four, about
 * {@code n^1.585} single-digit products; {@link #schoolbook} uses {@code n*m}. Both count the
 * single-digit products they make so the player can see the saving. Tallies are decimal strings.
 */
public final class PurserMultiply {

    public static final String QUEST_ID = "q_purser_long_sum";
    public static final int MAX_DIGITS = 20_000;

    /** A product and how many single-digit multiplications it took. */
    public record Result(String product, long digitProducts) { }

    private PurserMultiply() { }

    public static Result schoolbook(String a, String b) {
        int[] x = digits(a);
        int[] y = digits(b);
        int[] out = new int[x.length + y.length];
        for (int i = 0; i < x.length; i++) {
            for (int j = 0; j < y.length; j++) {
                out[i + j] += x[i] * y[j];
            }
            carry(out);
        }
        return new Result(text(out), (long) x.length * y.length);
    }

    public static Result karatsuba(String a, String b) {
        long[] count = {0};
        int[] p = kara(digits(a), digits(b), count);
        return new Result(text(p), count[0]);
    }

    private static int[] kara(int[] x, int[] y, long[] count) {
        int n = Math.max(x.length, y.length);
        if (n == 1) {
            count[0]++;
            int v = x[0] * y[0];
            return new int[] {v % 10, v / 10};
        }
        x = Arrays.copyOf(x, n);
        y = Arrays.copyOf(y, n);
        int m = n / 2;
        int[] x0 = Arrays.copyOfRange(x, 0, m);
        int[] x1 = Arrays.copyOfRange(x, m, n);
        int[] y0 = Arrays.copyOfRange(y, 0, m);
        int[] y1 = Arrays.copyOfRange(y, m, n);
        int[] z0 = kara(x0, y0, count);
        int[] z2 = kara(x1, y1, count);
        int[] z1 = kara(trim(add(x0, x1)), trim(add(y0, y1)), count);
        z1 = sub(sub(z1, z0), z2);
        int[] out = new int[2 * n + 2];
        accumulate(out, z0, 0);
        accumulate(out, z1, m);
        accumulate(out, z2, 2 * m);
        return out;
    }

    private static int[] add(int[] a, int[] b) {
        int[] r = new int[Math.max(a.length, b.length) + 1];
        accumulate(r, a, 0);
        accumulate(r, b, 0);
        return r;
    }

    /** a - b for a >= b. */
    private static int[] sub(int[] a, int[] b) {
        int[] r = a.clone();
        int borrow = 0;
        for (int i = 0; i < r.length; i++) {
            int v = r[i] - borrow - (i < b.length ? b[i] : 0);
            borrow = v < 0 ? 1 : 0;
            r[i] = v + borrow * 10;
        }
        for (int i = r.length; i < b.length; i++) {
            if (b[i] != 0) {
                throw new IllegalStateException("negative difference");
            }
        }
        if (borrow != 0) {
            throw new IllegalStateException("negative difference");
        }
        return r;
    }

    private static void accumulate(int[] into, int[] raw, int shift) {
        int[] v = trim(raw);
        int c = 0;
        int i = 0;
        for (; i < v.length; i++) {
            int s = into[i + shift] + v[i] + c;
            into[i + shift] = s % 10;
            c = s / 10;
        }
        for (int k = i + shift; c != 0; k++) {
            int s = into[k] + c;
            into[k] = s % 10;
            c = s / 10;
        }
    }

    private static void carry(int[] d) {
        int c = 0;
        for (int i = 0; i < d.length; i++) {
            int s = d[i] + c;
            d[i] = s % 10;
            c = s / 10;
        }
    }

    private static int[] trim(int[] d) {
        int len = d.length;
        while (len > 1 && d[len - 1] == 0) {
            len--;
        }
        return Arrays.copyOf(d, len);
    }

    /** Little-endian digits of a non-negative decimal tally. */
    static int[] digits(String s) {
        if (s == null || s.isEmpty() || s.length() > MAX_DIGITS) {
            throw new IllegalArgumentException("bad tally");
        }
        int[] d = new int[s.length()];
        for (int i = 0; i < s.length(); i++) {
            char ch = s.charAt(s.length() - 1 - i);
            if (ch < '0' || ch > '9') {
                throw new IllegalArgumentException("bad digit: " + ch);
            }
            d[i] = ch - '0';
        }
        return trim(d);
    }

    private static String text(int[] d) {
        int[] t = trim(d);
        StringBuilder sb = new StringBuilder(t.length);
        for (int i = t.length - 1; i >= 0; i--) {
            sb.append((char) ('0' + t[i]));
        }
        return sb.toString();
    }

    /** Quest q_purser_long_sum: the player's product of the two tallies must be exact. */
    public static boolean quest(String a, String b, String answer) {
        return karatsuba(a, b).product().equals(answer);
    }
}
