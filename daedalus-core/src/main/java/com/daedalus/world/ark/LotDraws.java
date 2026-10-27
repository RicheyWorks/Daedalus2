// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.math.BigInteger;
import java.util.Optional;

/**
 * G309 The Lot Draws: every shore party of k crew chosen from n gets a ticket number by the
 * combinatorial number system. A party is its crew numbers in ascending order c1 < c2 < ... < ck;
 * its ticket is C(c1, 1) + C(c2, 2) + ... + C(ck, k), which orders parties colexicographically.
 */
public final class LotDraws {

    public static final String QUEST_ID = "q_lot_draws";
    public static final int MAX_CREW = 5000;

    private LotDraws() { }

    static BigInteger binom(long n, int k) {
        if (k < 0 || n < k) {
            return BigInteger.ZERO;
        }
        BigInteger r = BigInteger.ONE;
        for (int i = 0; i < k; i++) {
            r = r.multiply(BigInteger.valueOf(n - i)).divide(BigInteger.valueOf(i + 1L));
        }
        return r;
    }

    private static void checkParty(int[] party) {
        for (int i = 0; i < party.length; i++) {
            if (party[i] < 0 || party[i] >= MAX_CREW || (i > 0 && party[i] <= party[i - 1])) {
                throw new IllegalArgumentException("party must be strictly ascending crew numbers");
            }
        }
    }

    /** Ticket number of a party (ascending crew numbers). */
    public static BigInteger rank(int[] party) {
        checkParty(party);
        BigInteger r = BigInteger.ZERO;
        for (int i = 0; i < party.length; i++) {
            r = r.add(binom(party[i], i + 1));
        }
        return r;
    }

    /** The k-crew party holding ticket t. */
    public static int[] unrank(int k, BigInteger t) {
        if (k < 0 || k > MAX_CREW || t.signum() < 0) {
            throw new IllegalArgumentException("bad k or ticket");
        }
        int[] out = new int[k];
        BigInteger rem = t;
        int hi = MAX_CREW;
        for (int i = k; i >= 1; i--) {
            int lo = i - 1;
            int top = hi - 1;
            if (binom(top, i).compareTo(rem) <= 0 && i == k) {
                throw new IllegalArgumentException("ticket too large for the crew bound");
            }
            while (lo < top) {
                int mid = (lo + top + 1) >>> 1;
                if (binom(mid, i).compareTo(rem) <= 0) {
                    lo = mid;
                } else {
                    top = mid - 1;
                }
            }
            out[i - 1] = lo;
            rem = rem.subtract(binom(lo, i));
            hi = lo;
        }
        return out;
    }

    /** The next party of the same size drawn from crew 0..n-1 in colex order, or empty after the last. */
    public static Optional<int[]> next(int[] party, int n) {
        checkParty(party);
        int k = party.length;
        if (k > 0 && party[k - 1] >= n) {
            throw new IllegalArgumentException("party member outside crew");
        }
        int[] p = party.clone();
        for (int i = 0; i < k; i++) {
            int limit = i + 1 < k ? p[i + 1] : n;
            if (p[i] + 1 < limit) {
                p[i]++;
                for (int j = 0; j < i; j++) {
                    p[j] = j;
                }
                return Optional.of(p);
            }
        }
        return Optional.empty();
    }

    /** Quest q_lot_draws: name the ticket of the drawn party. */
    public static boolean quest(int[] party, BigInteger ticket) {
        return rank(party).equals(ticket);
    }
}