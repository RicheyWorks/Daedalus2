// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.List;

/**
 * G231 The Cask Stack: {@code n} water casks (0 = smallest) sit stacked by size on the bow
 * (spot 0) and must move to the stern (spot 2) using midships (spot 1), one cask at a time,
 * never a bigger cask on a smaller (Tower of Hanoi). The fewest moves is {@code 2^n - 1};
 * {@link #move} gives the m-th move in O(1), {@link #deckAfter} the deck after m moves in O(n).
 */
public final class CaskStack {

    public static final String QUEST_ID = "q_cask_stack";
    public static final int BOW = 0;
    public static final int MIDSHIPS = 1;
    public static final int STERN = 2;
    public static final int MAX_CASKS = 60;

    /** One move: {@code cask} goes from spot {@code from} to spot {@code to}. */
    public record Move(int cask, int from, int to) { }

    private CaskStack() { }

    private static void checkCasks(int n) {
        if (n < 1 || n > MAX_CASKS) {
            throw new IllegalArgumentException("casks must be in 1.." + MAX_CASKS);
        }
    }

    public static long fewestMoves(int n) {
        checkCasks(n);
        return (1L << n) - 1;
    }

    /** The m-th move (1-based) of the optimal solution. */
    public static Move move(int n, long m) {
        if (m < 1 || m > fewestMoves(n)) {
            throw new IllegalArgumentException("move out of range");
        }
        int from = (int) ((m & (m - 1)) % 3);
        int to = (int) (((m | (m - 1)) + 1) % 3);
        if (n % 2 == 0) {
            from = swapMidStern(from);
            to = swapMidStern(to);
        }
        return new Move(Long.numberOfTrailingZeros(m), from, to);
    }

    private static int swapMidStern(int spot) {
        return spot == MIDSHIPS ? STERN : spot == STERN ? MIDSHIPS : spot;
    }

    /** Spot of each cask (index = cask) after the first {@code m} optimal moves. */
    public static int[] deckAfter(int n, long m) {
        if (m < 0 || m > fewestMoves(n)) {
            throw new IllegalArgumentException("move count out of range");
        }
        int[] spot = new int[n];
        int from = BOW;
        int to = STERN;
        int via = MIDSHIPS;
        long left = m;
        for (int c = n - 1; c >= 0; c--) {
            long half = 1L << c;
            if (left < half) {
                spot[c] = from;
                int t = to;
                to = via;
                via = t;
            } else {
                spot[c] = to;
                left -= half;
                int f = from;
                from = via;
                via = f;
            }
        }
        return spot;
    }

    /** True when {@code moves} is a legal log that ends with every cask on the stern. */
    public static boolean validLog(int n, List<int[]> moves) {
        checkCasks(n);
        List<Deque<Integer>> deck = List.of(new ArrayDeque<>(), new ArrayDeque<>(), new ArrayDeque<>());
        for (int c = n - 1; c >= 0; c--) {
            deck.get(BOW).push(c);
        }
        for (int[] mv : moves) {
            if (mv.length != 2 || mv[0] < 0 || mv[0] > 2 || mv[1] < 0 || mv[1] > 2 || mv[0] == mv[1]) {
                return false;
            }
            Deque<Integer> src = deck.get(mv[0]);
            Deque<Integer> dst = deck.get(mv[1]);
            if (src.isEmpty() || (!dst.isEmpty() && dst.peek() < src.peek())) {
                return false;
            }
            dst.push(src.pop());
        }
        return deck.get(STERN).size() == n;
    }

    /** Quest q_cask_stack: a legal log in the fewest moves. */
    public static boolean quest(int n, List<int[]> moves) {
        return moves.size() == fewestMoves(n) && validLog(n, moves);
    }
}
