// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Record Ingots: an ingot of n grains is a record ingot when it splits into equal bars in more ways than any smaller
 * ingot, i.e. it has more divisors than every m &lt; n (a highly composite number: 1, 2, 4, 6, 12, 24, 36, ...).
 *
 * <p>Reusable plain long API: {@link #divisorCount} for 1 &lt;= n &lt;= {@link #MAX_N}, {@link #recordsUpTo} and
 * {@link #isRecord}. Records are found by searching numbers whose prime exponents over 2, 3, 5, ... never increase
 * (every divisor-count record has that shape) and keeping running divisor-count records.
 */
public final class RecordIngots {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_record_ingots";
    /** Largest supported ingot. */
    public static final long MAX_N = 1_000_000_000_000L;

    private static final long[] PRIMES = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37};

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private static List<Long> allRecords;

    private RecordIngots() {
    }

    private static void check(long n) {
        if (n < 1 || n > MAX_N) {
            throw new IllegalArgumentException("ingot out of range: " + n);
        }
    }

    /** Number of divisors of n. */
    public static long divisorCount(long n) {
        check(n);
        long m = n;
        long d = 1;
        for (long p = 2; p * p <= m; p++) {
            int e = 0;
            while (m % p == 0) {
                m /= p;
                e++;
            }
            d *= e + 1;
        }
        return m > 1 ? d * 2 : d;
    }

    private static void search(int idx, long value, long divs, int maxExp, long limit, List<long[]> out) {
        out.add(new long[] {value, divs});
        if (idx >= PRIMES.length) {
            return;
        }
        long p = PRIMES[idx];
        long v = value;
        for (int e = 1; e <= maxExp; e++) {
            if (v > limit / p) {
                return;
            }
            v *= p;
            search(idx + 1, v, divs * (e + 1), e, limit, out);
        }
    }

    /** All record ingots in 1..limit, ascending (limit between 0 and {@link #MAX_N}). */
    public static List<Long> recordsUpTo(long limit) {
        if (limit < 0 || limit > MAX_N) {
            throw new IllegalArgumentException("limit out of range: " + limit);
        }
        List<long[]> cand = new ArrayList<>();
        if (limit >= 1) {
            search(0, 1, 1, Integer.MAX_VALUE, limit, cand);
        }
        cand.sort((x, y) -> Long.compare(x[0], y[0]));
        List<Long> rec = new ArrayList<>();
        long best = 0;
        for (long[] c : cand) {
            if (c[1] > best) {
                best = c[1];
                rec.add(c[0]);
            }
        }
        return Collections.unmodifiableList(rec);
    }

    private static synchronized List<Long> all() {
        if (allRecords == null) {
            allRecords = recordsUpTo(MAX_N);
        }
        return allRecords;
    }

    /** True when n has more divisors than every smaller ingot. */
    public static boolean isRecord(long n) {
        check(n);
        return Collections.binarySearch(all(), n) >= 0;
    }

    /** Grade a claim that ingot n is (or is not) a record ingot. */
    public static Grade grade(long n, boolean claimedRecord) {
        return isRecord(n) == claimedRecord ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: no smaller ingot splits as many ways. A record on the rack.";
            case SLIPPED -> "Forgemaster: the record slipped. Count every equal split, and check every smaller ingot.";
        };
    }
}
