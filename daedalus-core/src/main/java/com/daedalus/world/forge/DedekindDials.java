// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.math.BigInteger;

/**
 * Dedekind Dials: two forge dials turn at rates h and k; the smith reads their sawtooth correlation, the Dedekind
 * sum s(h,k) = sum_{r=1}^{k-1} ((r/k)) ((hr/k)), where ((x)) is the centred sawtooth. Instead of turning k notches,
 * the smith folds the dials with Dedekind reciprocity like Euclid's algorithm.
 *
 * <p>Reusable API: {@link #dedekindSum} returns s(h,k) as an exact reduced fraction {num, den} (BigInteger) for any
 * integer h and 1 &lt;= k &lt;= {@link #MAX_K}.
 */
public final class DedekindDials {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_dedekind_dials";
    /** Largest supported dial size. */
    public static final long MAX_K = Long.MAX_VALUE;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private DedekindDials() {
    }

    private static BigInteger[] reduce(BigInteger n, BigInteger d) {
        BigInteger g = n.gcd(d);
        if (g.signum() == 0) {
            return new BigInteger[] {BigInteger.ZERO, BigInteger.ONE};
        }
        BigInteger a = n.divide(g);
        BigInteger b = d.divide(g);
        if (b.signum() < 0) {
            a = a.negate();
            b = b.negate();
        }
        return new BigInteger[] {a, b};
    }

    /** s(h, k) as a reduced fraction {numerator, denominator}. */
    public static BigInteger[] dedekindSum(long h, long k) {
        if (k < 1) {
            throw new IllegalArgumentException("dial size must be positive: " + k);
        }
        BigInteger bk = BigInteger.valueOf(k);
        BigInteger bh = BigInteger.valueOf(h).mod(bk);
        BigInteger g = bh.gcd(bk);
        if (bh.signum() == 0) {
            return new BigInteger[] {BigInteger.ZERO, BigInteger.ONE};
        }
        bh = bh.divide(g);
        bk = bk.divide(g);
        BigInteger num = BigInteger.ZERO;
        BigInteger den = BigInteger.ONE;
        boolean plus = true;
        BigInteger twelve = BigInteger.valueOf(12);
        while (bh.signum() > 0 && bk.compareTo(BigInteger.ONE) > 0) {
            BigInteger hk = bh.multiply(bk);
            BigInteger rn = bh.multiply(bh).add(bk.multiply(bk)).add(BigInteger.ONE).subtract(hk.multiply(
                BigInteger.valueOf(3)));
            BigInteger rd = twelve.multiply(hk);
            BigInteger tn = plus ? rn : rn.negate();
            BigInteger[] s = reduce(num.multiply(rd).add(tn.multiply(den)), den.multiply(rd));
            num = s[0];
            den = s[1];
            plus = !plus;
            BigInteger nh = bk.mod(bh);
            bk = bh;
            bh = nh;
        }
        return reduce(num, den);
    }

    /** Grade a claimed value of s(h,k) given as a fraction. */
    public static Grade grade(long h, long k, long num, long den) {
        if (den == 0) {
            return Grade.SLIPPED;
        }
        BigInteger[] want = dedekindSum(h, k);
        BigInteger[] got = reduce(BigInteger.valueOf(num), BigInteger.valueOf(den));
        return want[0].equals(got[0]) && want[1].equals(got[1]) ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: the dials fold to one reading. Reciprocity keeps them honest.";
            case SLIPPED -> "Forgemaster: the dial slipped. Fold s(h,k) against s(k mod h, h) and mind the sign.";
        };
    }
}
