// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Kiln Bookings (contest gap G207): islanders ask to book the forge's one great kiln for time windows, each paying
 * scrip. Accept non-overlapping bookings for the most scrip.
 *
 * <p>The scheduler is plain: a request is {@code {start, end, pay}} with the half-open window [start, end), so a
 * booking ending at 5 fits one starting at 5. {@link #best} is exact weighted interval scheduling (sort by end, binary
 * search for the last compatible booking, DP). {@link #earliestEnd} and {@link #highestPay} are the tempting greedy
 * rules. Any project can use it for room booking or ability windows.
 */
public final class KilnBookings {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_kiln_bookings";

    /** How a set of bookings compares with the best. */
    public enum Grade { FULL_KILN, WARM, COLD }

    /** Accepted request indices (ascending) and the scrip they pay. */
    public record Plan(List<Integer> accepted, long pay) {

        public Plan {
            accepted = List.copyOf(accepted);
        }
    }

    private KilnBookings() {
    }

    /** {@code n} seeded requests within a day of {@code hours}: windows 1..6 hours long, paying 1..20 scrip. */
    public static int[][] requests(long seed, int n, int hours) {
        if (n < 0 || hours < 2) {
            throw new IllegalArgumentException("need n >= 0 and hours >= 2");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[][] q = new int[n][];
        for (int i = 0; i < n; i++) {
            int s = r.nextInt(hours - 1);
            int e = Math.min(hours, s + 1 + r.nextInt(6));
            q[i] = new int[] {s, e, 1 + r.nextInt(20)};
        }
        return q;
    }

    /** Pay of a set of requests, or -1 if any two overlap. */
    public static long pay(int[][] req, List<Integer> picked) {
        check(req);
        long p = 0;
        for (int a = 0; a < picked.size(); a++) {
            int[] x = req[picked.get(a)];
            for (int b = a + 1; b < picked.size(); b++) {
                int[] y = req[picked.get(b)];
                if (x[0] < y[1] && y[0] < x[1]) {
                    return -1;
                }
            }
            p += x[2];
        }
        return p;
    }

    /** The exact most-scrip plan. */
    public static Plan best(int[][] req) {
        check(req);
        int n = req.length;
        Integer[] ord = order(req, (a, b) -> req[a][1] != req[b][1] ? Integer.compare(req[a][1], req[b][1])
                : Integer.compare(a, b));
        int[] ends = new int[n];
        for (int k = 0; k < n; k++) {
            ends[k] = req[ord[k]][1];
        }
        long[] f = new long[n + 1];
        int[] prev = new int[n];
        for (int k = 0; k < n; k++) {
            int start = req[ord[k]][0];
            int lo = 0;
            int hi = k;
            while (lo < hi) {
                int mid = (lo + hi) >>> 1;
                if (ends[mid] <= start) {
                    lo = mid + 1;
                } else {
                    hi = mid;
                }
            }
            prev[k] = lo;
            f[k + 1] = Math.max(f[k], f[lo] + req[ord[k]][2]);
        }
        List<Integer> acc = new ArrayList<>();
        for (int k = n; k > 0;) {
            if (f[k] == f[k - 1]) {
                k--;
            } else {
                acc.add(ord[k - 1]);
                k = prev[k - 1];
            }
        }
        Collections.sort(acc);
        return new Plan(acc, f[n]);
    }

    /** Greedy: earliest end first, take whatever fits (best for counting bookings, not for scrip). */
    public static Plan earliestEnd(int[][] req) {
        check(req);
        return greedy(req, order(req, (a, b) -> req[a][1] != req[b][1] ? Integer.compare(req[a][1], req[b][1])
                : Integer.compare(a, b)));
    }

    /** Greedy: highest pay first, take whatever fits. */
    public static Plan highestPay(int[][] req) {
        check(req);
        return greedy(req, order(req, (a, b) -> req[a][2] != req[b][2] ? Integer.compare(req[b][2], req[a][2])
                : Integer.compare(a, b)));
    }

    private static Plan greedy(int[][] req, Integer[] ord) {
        List<Integer> acc = new ArrayList<>();
        for (int i : ord) {
            acc.add(i);
            if (pay(req, acc) < 0) {
                acc.remove(acc.size() - 1);
            }
        }
        Collections.sort(acc);
        return new Plan(acc, pay(req, acc));
    }

    private static Integer[] order(int[][] req, Comparator<Integer> cmp) {
        Integer[] o = new Integer[req.length];
        for (int i = 0; i < o.length; i++) {
            o[i] = i;
        }
        Arrays.sort(o, cmp);
        return o;
    }

    /** FULL_KILN at the best, WARM at 90% or more, COLD below. */
    public static Grade grade(long pay, long best) {
        if (pay > best) {
            throw new IllegalArgumentException("pay above the best");
        }
        if (pay == best) {
            return Grade.FULL_KILN;
        }
        return 10L * pay >= 9L * best ? Grade.WARM : Grade.COLD;
    }

    /** The Forgemaster's line for a plan. */
    public static String forgemasterLine(Plan p, long best) {
        return switch (grade(p.pay(), best)) {
            case FULL_KILN -> "Forgemaster: " + p.pay() + " scrip. The kiln never cools.";
            case WARM -> "Forgemaster: " + p.pay() + " of " + best + " scrip. A good day, not the best.";
            case COLD -> "Forgemaster: " + p.pay() + " of " + best + " scrip. The kiln sat cold for hours.";
        };
    }

    private static void check(int[][] req) {
        for (int[] q : req) {
            if (q.length != 3 || q[0] >= q[1] || q[2] < 0) {
                throw new IllegalArgumentException("a request is {start < end, pay >= 0}");
            }
        }
    }
}
