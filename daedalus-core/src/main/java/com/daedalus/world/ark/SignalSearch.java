// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * G286 The Signal Search: the signal mate scans the ark's lamp log (a string of signal letters)
 * with a Rabin-Karp rolling hash under two primes. Every hash hit is confirmed letter by letter,
 * so answers are exact. Finds every occurrence of a pattern and the longest signal run that
 * appears at least twice (binary search on length; overlaps allowed).
 */
public final class SignalSearch {

    public static final String QUEST_ID = "q_signal_search";
    private static final long M1 = 1_000_000_007L;
    private static final long M2 = 998_244_353L;
    private static final long B1 = 131;
    private static final long B2 = 137;

    private SignalSearch() { }

    private static long pow(long b, int e, long m) {
        long r = 1;
        for (int i = 0; i < e; i++) {
            r = r * b % m;
        }
        return r;
    }

    private static long[] hashesOf(String s, int len, long b, long m) {
        int count = s.length() - len + 1;
        long[] out = new long[Math.max(count, 0)];
        if (count <= 0) {
            return out;
        }
        long top = pow(b, len - 1, m);
        long h = 0;
        for (int i = 0; i < len; i++) {
            h = (h * b + s.charAt(i)) % m;
        }
        out[0] = h;
        for (int i = 1; i < count; i++) {
            h = (h - s.charAt(i - 1) * top % m + m) % m;
            h = (h * b + s.charAt(i + len - 1)) % m;
            out[i] = h;
        }
        return out;
    }

    private static long hash(String s, long b, long m) {
        long h = 0;
        for (int i = 0; i < s.length(); i++) {
            h = (h * b + s.charAt(i)) % m;
        }
        return h;
    }

    /** Start index of every occurrence of pattern in log, ascending (overlaps included). */
    public static List<Integer> find(String log, String pattern) {
        if (pattern.isEmpty()) {
            throw new IllegalArgumentException("empty pattern");
        }
        List<Integer> out = new ArrayList<>();
        long[] h1 = hashesOf(log, pattern.length(), B1, M1);
        long[] h2 = hashesOf(log, pattern.length(), B2, M2);
        long p1 = hash(pattern, B1, M1);
        long p2 = hash(pattern, B2, M2);
        for (int i = 0; i < h1.length; i++) {
            if (h1[i] == p1 && h2[i] == p2 && log.startsWith(pattern, i)) {
                out.add(i);
            }
        }
        return List.copyOf(out);
    }

    /** First start i (smallest) of a run of length len that also occurs at another start; -1 if none. */
    static int repeatAt(String log, int len) {
        if (len == 0) {
            return log.isEmpty() ? -1 : 0;
        }
        long[] h1 = hashesOf(log, len, B1, M1);
        long[] h2 = hashesOf(log, len, B2, M2);
        Map<Long, List<Integer>> seen = new HashMap<>();
        int best = -1;
        for (int i = 0; i < h1.length; i++) {
            long key = h1[i] * M2 + h2[i];
            List<Integer> starts = seen.computeIfAbsent(key, k -> new ArrayList<>());
            for (int j : starts) {
                if (log.regionMatches(i, log, j, len)) {
                    if (best < 0 || j < best) {
                        best = j;
                    }
                    break;
                }
            }
            starts.add(i);
        }
        return best;
    }

    /** Longest run appearing at least twice; ties go to the one starting earliest. "" if none. */
    public static String longestRepeat(String log) {
        int lo = 0;
        int hi = Math.max(log.length() - 1, 0);
        while (lo < hi) {
            int mid = (lo + hi + 1) >>> 1;
            if (repeatAt(log, mid) >= 0) {
                lo = mid;
            } else {
                hi = mid - 1;
            }
        }
        if (lo == 0) {
            return "";
        }
        int at = repeatAt(log, lo);
        return log.substring(at, at + lo);
    }

    /** Quest q_signal_search: the mate names how many times the pattern shows in the log. */
    public static boolean quest(String log, String pattern, int answer) {
        return find(log, pattern).size() == answer;
    }
}