// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Coal Heaps (contest gap G296): the stoker and the Forgemaster take turns shovelling coal. Each turn takes an allowed
 * amount from one heap; whoever cannot move loses. Tell whether the player to move wins and name a winning shovel.
 *
 * <p>The tool is plain: {@link #grundyTable} builds Sprague-Grundy numbers for a subtraction game by mex,
 * {@link #nimSum} XORs them across heaps, and {@link #winningMove} names a move that leaves a zero position. Any
 * project can use it for impartial-game AI on heaps.
 */
public final class CoalHeaps {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_coal_heaps";

    /** How a call went. */
    public enum Grade { STOKED, SMOTHERED }

    /** A shovel: take {@code amount} from heap {@code heap}. */
    public record Move(int heap, int amount) {
    }

    private CoalHeaps() {
    }

    /** Seeded heaps of size 0..maxHeap. Same seed, same pile. */
    public static int[] heaps(long seed, int count, int maxHeap) {
        if (count < 1 || maxHeap < 0) {
            throw new IllegalArgumentException("need count >= 1 and maxHeap >= 0");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[] h = new int[count];
        for (int i = 0; i < count; i++) {
            h[i] = r.nextInt(maxHeap + 1);
        }
        return h;
    }

    /** Grundy numbers g[0..max] for heaps where a move removes any amount in {@code take} (positive, distinct). */
    public static int[] grundyTable(int[] take, int max) {
        for (int t : take) {
            if (t < 1) {
                throw new IllegalArgumentException("take amounts must be positive");
            }
        }
        int[] g = new int[max + 1];
        boolean[] seen = new boolean[take.length + 2];
        for (int n = 1; n <= max; n++) {
            Arrays.fill(seen, false);
            for (int t : take) {
                if (t <= n && g[n - t] < seen.length) {
                    seen[g[n - t]] = true;
                }
            }
            int m = 0;
            while (seen[m]) {
                m++;
            }
            g[n] = m;
        }
        return g;
    }

    private static int maxOf(int[] h) {
        int m = 0;
        for (int x : h) {
            if (x < 0) {
                throw new IllegalArgumentException("heaps must be non-negative");
            }
            m = Math.max(m, x);
        }
        return m;
    }

    /** XOR of the heaps' Grundy numbers; non-zero means the player to move wins. */
    public static int nimSum(int[] heaps, int[] take) {
        int[] g = grundyTable(take, maxOf(heaps));
        int x = 0;
        for (int h : heaps) {
            x ^= g[h];
        }
        return x;
    }

    /** A move to a zero position (lowest heap, then smallest amount), or null if the player to move loses. */
    public static Move winningMove(int[] heaps, int[] take) {
        int[] g = grundyTable(take, maxOf(heaps));
        int x = 0;
        for (int h : heaps) {
            x ^= g[h];
        }
        if (x == 0) {
            return null;
        }
        int[] sorted = take.clone();
        Arrays.sort(sorted);
        for (int i = 0; i < heaps.length; i++) {
            int want = x ^ g[heaps[i]];
            for (int t : sorted) {
                if (t <= heaps[i] && g[heaps[i] - t] == want) {
                    return new Move(i, t);
                }
            }
        }
        throw new IllegalStateException("Sprague-Grundy guarantees a move");
    }

    /** STOKED if the player named a winning move, or correctly passed a null move on a losing position. */
    public static Grade grade(int[] heaps, int[] take, Move claimed) {
        if (nimSum(heaps, take) == 0) {
            return claimed == null ? Grade.STOKED : Grade.SMOTHERED;
        }
        if (claimed == null || claimed.heap() < 0 || claimed.heap() >= heaps.length
                || Arrays.stream(take).noneMatch(t -> t == claimed.amount())
                || claimed.amount() > heaps[claimed.heap()]) {
            return Grade.SMOTHERED;
        }
        int[] after = heaps.clone();
        after[claimed.heap()] -= claimed.amount();
        return nimSum(after, take) == 0 ? Grade.STOKED : Grade.SMOTHERED;
    }

    /** The Forgemaster's line for a call. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case STOKED -> "Forgemaster: you read the heaps like a ledger. The last shovel will be yours.";
            case SMOTHERED -> "Forgemaster: that scoop hands me the fire. Count the heaps again.";
        };
    }
}
