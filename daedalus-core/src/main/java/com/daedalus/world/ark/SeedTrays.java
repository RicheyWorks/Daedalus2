// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

/**
 * G418 The Seed Trays: the ark gardeners play Kalah. A board of p pits a side is an int array of
 * length 2p + 2: pits 0..p-1 and store p belong to side 0, pits p+1..2p and store 2p+1 to side 1.
 * A turn lifts every seed from one of the mover's non-empty pits and sows one per hole
 * anticlockwise, skipping the opponent's store. Ending in one's own store gives another turn;
 * ending in one's own empty pit captures that seed and the seeds opposite when there are any.
 * When either side's pits are empty, every remaining seed goes to its owner's store.
 */
public final class SeedTrays {

    public static final String QUEST_ID = "q_seed_trays";
    public static final int MAX_PITS = 8;
    public static final int MAX_SEEDS = 12;
    public static final int MAX_SOLVE_SEEDS = 18;

    private final Map<String, Integer> memo = new HashMap<>();

    /** A fresh solver that keeps its memo between calls. */
    public SeedTrays() {
        // memo starts empty
    }

    /** Starting board with p pits a side and s seeds in each pit. */
    public static int[] start(int p, int s) {
        if (p < 1 || p > MAX_PITS || s < 1 || s > MAX_SEEDS) {
            throw new IllegalArgumentException("pits or seeds out of range");
        }
        int[] b = new int[2 * p + 2];
        for (int i = 0; i < p; i++) {
            b[i] = s;
            b[p + 1 + i] = s;
        }
        return b;
    }

    private static int pits(int[] b) {
        if (b == null || b.length < 4 || (b.length & 1) != 0 || b.length > 2 * MAX_PITS + 2) {
            throw new IllegalArgumentException("board must have 2p + 2 holes");
        }
        for (int v : b) {
            if (v < 0) {
                throw new IllegalArgumentException("negative seeds");
            }
        }
        return (b.length - 2) / 2;
    }

    /** True when either side has no seeds left in its pits. */
    public static boolean over(int[] b) {
        int p = pits(b);
        return sideSum(b, p, 0) == 0 || sideSum(b, p, 1) == 0;
    }

    private static int sideSum(int[] b, int p, int side) {
        int s = 0;
        for (int i = 0; i < p; i++) {
            s += b[side * (p + 1) + i];
        }
        return s;
    }

    /**
     * Plays the mover's pit (0..p-1 counted from the mover's own side) and returns the new board
     * with one extra last element: the side to move next.
     */
    public static int[] sow(int[] board, int side, int pit) {
        int p = pits(board);
        if ((side != 0 && side != 1) || pit < 0 || pit >= p || over(board)) {
            throw new IllegalArgumentException("bad move");
        }
        int[] b = board.clone();
        int n = b.length;
        int at = side * (p + 1) + pit;
        int seeds = b[at];
        if (seeds == 0) {
            throw new IllegalArgumentException("pit is empty");
        }
        b[at] = 0;
        int oppStore = side == 0 ? 2 * p + 1 : p;
        int ownStore = side == 0 ? p : 2 * p + 1;
        while (seeds > 0) {
            at = (at + 1) % n;
            if (at != oppStore) {
                b[at]++;
                seeds--;
            }
        }
        int next = 1 - side;
        if (at == ownStore) {
            next = side;
        } else if (at / (p + 1) == side && b[at] == 1) {
            int opposite = 2 * p - at;
            if (b[opposite] > 0) {
                b[ownStore] += b[opposite] + 1;
                b[opposite] = 0;
                b[at] = 0;
            }
        }
        if (sideSum(b, p, 0) == 0 || sideSum(b, p, 1) == 0) {
            for (int s = 0; s < 2; s++) {
                b[s == 0 ? p : 2 * p + 1] += sideSum(b, p, s);
                for (int i = 0; i < p; i++) {
                    b[s * (p + 1) + i] = 0;
                }
            }
        }
        int[] out = Arrays.copyOf(b, n + 1);
        out[n] = next;
        return out;
    }

    /** Final store margin (side's store minus the other) under perfect play by both sides. */
    public int margin(int[] board, int side) {
        int p = pits(board);
        if (side != 0 && side != 1) {
            throw new IllegalArgumentException("side must be 0 or 1");
        }
        if (Arrays.stream(board).sum() > MAX_SOLVE_SEEDS) {
            throw new IllegalArgumentException("solver limited to " + MAX_SOLVE_SEEDS + " seeds");
        }
        return solve(board, p, side);
    }

    private int solve(int[] b, int p, int side) {
        if (over(b)) {
            int s0 = b[p] + sideSum(b, p, 0);
            int s1 = b[2 * p + 1] + sideSum(b, p, 1);
            return side == 0 ? s0 - s1 : s1 - s0;
        }
        String key = side + Arrays.toString(b);
        Integer c = memo.get(key);
        if (c != null) {
            return c;
        }
        int best = Integer.MIN_VALUE;
        for (int i = 0; i < p; i++) {
            if (b[side * (p + 1) + i] > 0) {
                int[] r = sow(b, side, i);
                int next = r[r.length - 1];
                int[] nb = Arrays.copyOf(r, r.length - 1);
                int v = next == side ? solve(nb, p, side) : -solve(nb, p, next);
                best = Math.max(best, v);
            }
        }
        memo.put(key, best);
        return best;
    }

    /** Lowest pit keeping the perfect-play margin, or -1 when the game is over. */
    public int bestPit(int[] board, int side) {
        int want = margin(board, side);
        int p = pits(board);
        if (over(board)) {
            return -1;
        }
        for (int i = 0; i < p; i++) {
            if (board[side * (p + 1) + i] > 0) {
                int[] r = sow(board, side, i);
                int next = r[r.length - 1];
                int[] nb = Arrays.copyOf(r, r.length - 1);
                int v = next == side ? solve(nb, p, side) : -solve(nb, p, next);
                if (v == want) {
                    return i;
                }
            }
        }
        return -1;
    }

    /** Quest q_seed_trays: the gardener names the first player's perfect-play margin at Kalah(3, 2). */
    public static boolean quest(int answer) {
        return new SeedTrays().margin(start(3, 2), 0) == answer;
    }
}