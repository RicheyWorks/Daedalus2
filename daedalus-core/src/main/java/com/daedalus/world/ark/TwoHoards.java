// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G354 The Two Hoards: two coin hoards sit on the table; a turn takes any number from one hoard or
 * the same number from both, and whoever takes the last coin wins (Wythoff's game). The losing
 * spots are (floor(k phi), floor(k phi) + k), computed exactly with an integer square root, and from
 * any other spot the steward finds a move onto one.
 */
public final class TwoHoards {

    public static final String QUEST_ID = "q_two_hoards";

    private static final long LIMIT = 1_000_000_000L;

    private TwoHoards() { }

    private static long isqrt(long v) {
        long r = (long) Math.sqrt((double) v);
        while (r * r > v) {
            r--;
        }
        while ((r + 1) * (r + 1) <= v) {
            r++;
        }
        return r;
    }

    /** Smaller hoard of the k-th losing spot: floor(k * phi) for k from 0 to 10^9. */
    public static long lowerOf(long k) {
        if (k < 0 || k > LIMIT) {
            throw new IllegalArgumentException("k 0..10^9");
        }
        return (k + isqrt(5 * k * k)) / 2;
    }

    private static void check(long a, long b) {
        if (a < 0 || b < 0 || a > LIMIT || b > LIMIT) {
            throw new IllegalArgumentException("hoards 0..10^9");
        }
    }

    /** True when the player to move loses with best play. */
    public static boolean isLosing(long x, long y) {
        check(x, y);
        long a = Math.min(x, y);
        long k = Math.max(x, y) - a;
        return lowerOf(k) == a;
    }

    /** A winning move as the new {x, y}, or an empty array from a losing spot. */
    public static long[] winningMove(long x, long y) {
        if (isLosing(x, y)) {
            return new long[0];
        }
        boolean swapped = x > y;
        long a = Math.min(x, y);
        long b = Math.max(x, y);
        long k = b - a;
        long[] to;
        if (a > lowerOf(k)) {
            long d = a - lowerOf(k);
            to = new long[] {a - d, b - d};
        } else {
            long lo = 0;
            long hi = a;
            while (lo < hi) {
                long mid = (lo + hi) / 2;
                if (lowerOf(mid) + mid < a) {
                    lo = mid + 1;
                } else {
                    hi = mid;
                }
            }
            if (lowerOf(lo) + lo == a) {
                to = new long[] {a, lowerOf(lo)};
            } else {
                lo = 0;
                hi = a;
                while (lo < hi) {
                    long mid = (lo + hi) / 2;
                    if (lowerOf(mid) < a) {
                        lo = mid + 1;
                    } else {
                        hi = mid;
                    }
                }
                to = new long[] {a, a + lo};
            }
        }
        return swapped ? new long[] {to[1], to[0]} : to;
    }

    /** True when (x, y) can be reached from (fromX, fromY) in one legal turn. */
    public static boolean isLegal(long fromX, long fromY, long x, long y) {
        check(fromX, fromY);
        check(x, y);
        long dx = fromX - x;
        long dy = fromY - y;
        if (dx < 0 || dy < 0 || dx + dy == 0) {
            return false;
        }
        return dx == 0 || dy == 0 || dx == dy;
    }

    /** Quest q_two_hoards: from a winning spot, name a move onto a losing spot. */
    public static boolean quest(long x, long y, long toX, long toY) {
        return isLegal(x, y, toX, toY) && isLosing(toX, toY);
    }
}