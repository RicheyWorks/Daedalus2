// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayList;
import java.util.List;

/**
 * G268 The Measuring Casks: the ark's water steward has two unmarked casks of {@code a} and
 * {@code b} litres and must get exactly {@code c} litres into one of them using fills, empties
 * and pours. By Bezout ({@link #bezout}, extended Euclid) that is possible iff
 * {@code gcd(a, b) | c} and {@code c <= max(a, b)}. {@link #plan} plays the two one-way pouring
 * strategies (always pour A into B, or B into A) and keeps the shorter; that is the fewest moves.
 */
public final class MeasuringCasks {

    public static final String QUEST_ID = "q_measuring_casks";
    public static final int MAX_CASK = 100_000;

    /** The steward's moves. */
    public enum Move { FILL_A, FILL_B, EMPTY_A, EMPTY_B, POUR_A_TO_B, POUR_B_TO_A }

    /** Bezout identity: {@code a*x + b*y == g == gcd(a, b)}. */
    public record Bezout(long g, long x, long y) { }

    private MeasuringCasks() { }

    public static Bezout bezout(long a, long b) {
        if (a < 0 || b < 0) {
            throw new IllegalArgumentException("negative");
        }
        long oldR = a;
        long r = b;
        long oldS = 1;
        long s = 0;
        long oldT = 0;
        long t = 1;
        while (r != 0) {
            long q = oldR / r;
            long tmp = r;
            r = oldR - q * r;
            oldR = tmp;
            tmp = s;
            s = oldS - q * s;
            oldS = tmp;
            tmp = t;
            t = oldT - q * t;
            oldT = tmp;
        }
        return new Bezout(oldR, oldS, oldT);
    }

    public static boolean solvable(int a, int b, int c) {
        check(a, b, c);
        return c <= Math.max(a, b) && c % bezout(a, b).g() == 0;
    }

    /** Fewest moves to get c litres into one cask, or null if impossible. */
    public static List<Move> plan(int a, int b, int c) {
        if (!solvable(a, b, c)) {
            return null;
        }
        List<Move> ab = pourOneWay(a, b, c, true);
        List<Move> ba = pourOneWay(a, b, c, false);
        return ab.size() <= ba.size() ? ab : ba;
    }

    private static List<Move> pourOneWay(int a, int b, int c, boolean aToB) {
        List<Move> moves = new ArrayList<>();
        int from = 0;
        int to = 0;
        int capFrom = aToB ? a : b;
        int capTo = aToB ? b : a;
        while (from != c && to != c) {
            if (from == 0) {
                from = capFrom;
                moves.add(aToB ? Move.FILL_A : Move.FILL_B);
            } else if (to == capTo) {
                to = 0;
                moves.add(aToB ? Move.EMPTY_B : Move.EMPTY_A);
            } else {
                int x = Math.min(from, capTo - to);
                from -= x;
                to += x;
                moves.add(aToB ? Move.POUR_A_TO_B : Move.POUR_B_TO_A);
            }
        }
        return List.copyOf(moves);
    }

    /** Plays {@code moves}; returns the final {A, B} levels. */
    public static int[] play(int a, int b, List<Move> moves) {
        check(a, b, 0);
        int x = 0;
        int y = 0;
        for (Move m : moves) {
            switch (m) {
                case FILL_A -> x = a;
                case FILL_B -> y = b;
                case EMPTY_A -> x = 0;
                case EMPTY_B -> y = 0;
                case POUR_A_TO_B -> {
                    int p = Math.min(x, b - y);
                    x -= p;
                    y += p;
                }
                case POUR_B_TO_A -> {
                    int p = Math.min(y, a - x);
                    y -= p;
                    x += p;
                }
                default -> throw new IllegalStateException();
            }
        }
        return new int[] {x, y};
    }

    private static void check(int a, int b, int c) {
        if (a < 1 || b < 1 || a > MAX_CASK || b > MAX_CASK || c < 0) {
            throw new IllegalArgumentException("bad casks or target");
        }
    }

    /** Quest q_measuring_casks: the steward's moves must reach c in as few moves as possible. */
    public static boolean quest(int a, int b, int c, List<Move> moves) {
        List<Move> best = plan(a, b, c);
        if (best == null || moves.size() > best.size()) {
            return false;
        }
        int[] end = play(a, b, moves);
        return end[0] == c || end[1] == c;
    }
}
