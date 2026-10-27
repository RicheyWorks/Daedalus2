// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.SplittableRandom;

/**
 * Clamp Pairs (contest gap G267): a rack of opening and closing clamps of several kinds. Find the longest stretch where
 * every clamp is properly paired, and the fewest clamps to add so a rack of plain clamps pairs up.
 *
 * <p>The tool is plain: {@link #longestBalanced} is an O(n) stack scan over a {@code String} of the brackets in
 * {@link #OPEN} / {@link #CLOSE}, and {@link #insertionsToBalance} the O(n) balance count for round brackets. Any
 * project can use it for bracket validation.
 */
public final class ClampPairs {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_clamp_pairs";

    /** Opening clamps, matched by position with {@link #CLOSE}. */
    public static final String OPEN = "([{";

    /** Closing clamps. */
    public static final String CLOSE = ")]}";

    /** How an answer went. */
    public enum Grade { LOCKED, LOOSE }

    /** Clamps [from, to). */
    public record Span(int from, int to) {

        /** Span length. */
        public int length() {
            return to - from;
        }
    }

    private ClampPairs() {
    }

    /** A seeded rack of {@code n} clamps using the first {@code kinds} clamp kinds. Same seed, same rack. */
    public static String rack(long seed, int n, int kinds) {
        if (n < 0 || kinds < 1 || kinds > OPEN.length()) {
            throw new IllegalArgumentException("need n >= 0 and 1 <= kinds <= " + OPEN.length());
        }
        SplittableRandom r = new SplittableRandom(seed);
        StringBuilder sb = new StringBuilder(n);
        for (int i = 0; i < n; i++) {
            int k = r.nextInt(kinds);
            sb.append(r.nextBoolean() ? OPEN.charAt(k) : CLOSE.charAt(k));
        }
        return sb.toString();
    }

    private static int kind(char c) {
        int o = OPEN.indexOf(c);
        if (o >= 0) {
            return o;
        }
        int x = CLOSE.indexOf(c);
        if (x < 0) {
            throw new IllegalArgumentException("not a clamp: " + c);
        }
        return -1 - x;
    }

    /** Longest properly paired stretch (earliest on ties); Span(0, 0) if none. */
    public static Span longestBalanced(String s) {
        int n = s.length();
        int[] st = new int[n + 1];
        int top = 0;
        st[top++] = -1;
        int bestFrom = 0;
        int bestLen = 0;
        for (int i = 0; i < n; i++) {
            int k = kind(s.charAt(i));
            if (k >= 0) {
                st[top++] = i;
                continue;
            }
            int t = st[top - 1];
            if (t >= 0 && kind(s.charAt(t)) == -1 - k) {
                top--;
                int from = st[top - 1] + 1;
                if (i + 1 - from > bestLen) {
                    bestLen = i + 1 - from;
                    bestFrom = from;
                }
            } else {
                st[top++] = i;
            }
        }
        return new Span(bestFrom, bestFrom + bestLen);
    }

    /** True if the whole string is properly paired. */
    public static boolean balanced(String s) {
        return longestBalanced(s).length() == s.length();
    }

    /** Fewest round clamps to insert so a rack of '(' and ')' pairs up. */
    public static int insertionsToBalance(String s) {
        int open = 0;
        int added = 0;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '(') {
                open++;
            } else if (c == ')') {
                if (open > 0) {
                    open--;
                } else {
                    added++;
                }
            } else {
                throw new IllegalArgumentException("only round clamps: " + c);
            }
        }
        return added + open;
    }

    /** LOCKED only if the claimed stretch is paired and as long as the longest. */
    public static Grade grade(String s, Span pick) {
        if (pick.from() < 0 || pick.to() > s.length() || pick.from() > pick.to()) {
            return Grade.LOOSE;
        }
        return balanced(s.substring(pick.from(), pick.to())) && pick.length() == longestBalanced(s).length()
                ? Grade.LOCKED : Grade.LOOSE;
    }

    /** The Forgemaster's line for an answer. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case LOCKED -> "Forgemaster: every clamp bites its partner. That frame will not slip.";
            case LOOSE -> "Forgemaster: a clamp is hanging open. Pair them again before the glue sets.";
        };
    }
}
