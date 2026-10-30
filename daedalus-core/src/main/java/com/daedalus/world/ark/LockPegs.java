// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;

/**
 * G362 The Lock Pegs: the strongroom lock hides a code of 4 pegs in 6 colours (1296 codes). Each try
 * is scored as pegs in the right place and further pegs of a right colour in the wrong place
 * (Mastermind). The quartermaster keeps only codes consistent with every score and picks the next
 * try by Knuth's minimax rule, which opens any lock within 5 tries.
 */
public final class LockPegs {

    public static final String QUEST_ID = "q_lock_pegs";

    public static final int CODES = 1296;

    /** Knuth's opening try 1122: pegs 0, 0, 1, 1 (peg 0 is the lowest base-6 digit). */
    private static final int FIRST_TRY = 36 + 216;

    private LockPegs() { }

    private static void check(int code) {
        if (code < 0 || code >= CODES) {
            throw new IllegalArgumentException("code 0..1295: " + code);
        }
    }

    /** Peg i (0..3) of a code, a colour 0..5. */
    public static int peg(int code, int i) {
        check(code);
        int c = code;
        for (int k = 0; k < i; k++) {
            c /= 6;
        }
        return c % 6;
    }

    /** Score as right-place * 10 + right-colour-wrong-place. */
    public static int score(int secret, int guess) {
        check(secret);
        check(guess);
        int black = 0;
        int[] cs = new int[6];
        int[] cg = new int[6];
        int s = secret;
        int g = guess;
        for (int i = 0; i < 4; i++) {
            int a = s % 6;
            int b = g % 6;
            if (a == b) {
                black++;
            } else {
                cs[a]++;
                cg[b]++;
            }
            s /= 6;
            g /= 6;
        }
        int white = 0;
        for (int c = 0; c < 6; c++) {
            white += Math.min(cs[c], cg[c]);
        }
        return black * 10 + white;
    }

    /** Codes still consistent with a try and its score. */
    public static int[] filter(int[] candidates, int guess, int scored) {
        int[] out = new int[candidates.length];
        int n = 0;
        for (int c : candidates) {
            if (score(c, guess) == scored) {
                out[n++] = c;
            }
        }
        return Arrays.copyOf(out, n);
    }

    /** Knuth's minimax next try for the remaining candidates (1122 first). */
    public static int nextGuess(int[] candidates) {
        if (candidates.length == 0) {
            throw new IllegalArgumentException("no candidates left");
        }
        if (candidates.length == CODES) {
            return FIRST_TRY;
        }
        if (candidates.length == 1) {
            return candidates[0];
        }
        boolean[] isCand = new boolean[CODES];
        for (int c : candidates) {
            isCand[c] = true;
        }
        int best = -1;
        int bestWorst = Integer.MAX_VALUE;
        boolean bestIsCand = false;
        int[] parts = new int[41];
        for (int g = 0; g < CODES; g++) {
            Arrays.fill(parts, 0);
            int worst = 0;
            for (int c : candidates) {
                int k = ++parts[score(c, g)];
                if (k > worst) {
                    worst = k;
                }
            }
            if (worst < bestWorst || (worst == bestWorst && isCand[g] && !bestIsCand)) {
                best = g;
                bestWorst = worst;
                bestIsCand = isCand[g];
            }
        }
        return best;
    }

    /** Number of tries Knuth's rule needs to open the lock. */
    public static int solve(int secret) {
        check(secret);
        int[] cand = new int[CODES];
        for (int i = 0; i < CODES; i++) {
            cand[i] = i;
        }
        for (int tries = 1; tries <= 10; tries++) {
            int g = nextGuess(cand);
            int s = score(secret, g);
            if (s == 40) {
                return tries;
            }
            cand = filter(cand, g, s);
        }
        throw new IllegalStateException("lock not opened");
    }

    /** Quest q_lock_pegs: score the try against the lock. */
    public static boolean quest(int secret, int guess, int answer) {
        return score(secret, guess) == answer;
    }
}