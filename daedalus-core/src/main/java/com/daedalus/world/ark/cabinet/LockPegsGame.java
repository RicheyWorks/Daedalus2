// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import com.daedalus.world.ark.LockPegs;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Solo cabinet adapter for G362 The Lock Pegs (Mastermind, 4 pegs in 6 colours); scoring and Knuth's minimax next try
 * live in {@link LockPegs}. Tries are typed as four colours 1..6, for example {@code 1122}. Open the lock within
 * {@link #MAX_TRIES} tries to win.
 */
public final class LockPegsGame implements ArkCabinetGame {

    /** Tries the strongroom allows before it jams. */
    public static final int MAX_TRIES = 10;
    /** Default lock code 4-6-2-3 as typed. */
    private static final String STARTER = "4623";

    private final int secret;
    private int[] candidates;
    private final List<String> log = new ArrayList<>();
    private boolean opened;

    /** The cabinet's starter lock. */
    public LockPegsGame() {
        this(decode(STARTER));
    }

    /** A lock with the given code 0..1295. */
    public LockPegsGame(int secret) {
        if (secret < 0 || secret >= LockPegs.CODES) {
            throw new IllegalArgumentException("code 0.." + (LockPegs.CODES - 1));
        }
        this.secret = secret;
        this.candidates = new int[LockPegs.CODES];
        for (int c = 0; c < LockPegs.CODES; c++) {
            candidates[c] = c;
        }
    }

    /** A lock with a code drawn from the seed. */
    public static LockPegsGame seeded(long seed) {
        return new LockPegsGame(new SplittableRandom(seed).nextInt(LockPegs.CODES));
    }

    /** Typed try such as {@code 1122} to a code, or -1 when it is not four colours 1..6. */
    public static int decode(String move) {
        if (move == null) {
            return -1;
        }
        String m = move.trim();
        if (m.length() != 4) {
            return -1;
        }
        int code = 0;
        int place = 1;
        for (int i = 0; i < 4; i++) {
            int c = m.charAt(i) - '1';
            if (c < 0 || c > 5) {
                return -1;
            }
            code += c * place;
            place *= 6;
        }
        return code;
    }

    /** A code typed as four colours 1..6. */
    public static String encode(int code) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 4; i++) {
            sb.append((char) ('1' + LockPegs.peg(code, i)));
        }
        return sb.toString();
    }

    @Override
    public String id() {
        return "lock";
    }

    @Override
    public String title() {
        return "The Lock Pegs";
    }

    @Override
    public String rules() {
        return "Type four colours 1..6, for example 1122. Each try scores right place / right colour. "
            + "Open the lock within " + MAX_TRIES + " tries.";
    }

    @Override
    public List<String> legalMoves() {
        List<String> out = new ArrayList<>();
        if (!over()) {
            for (int c = 0; c < LockPegs.CODES; c++) {
                out.add(encode(c));
            }
        }
        return Collections.unmodifiableList(out);
    }

    @Override
    public boolean play(String move) {
        int g = decode(move);
        if (over() || g < 0) {
            return false;
        }
        int s = LockPegs.score(secret, g);
        candidates = LockPegs.filter(candidates, g, s);
        log.add(encode(g) + "  " + s / 10 + " right place, " + s % 10 + " right colour");
        opened = g == secret;
        return true;
    }

    /** Tries made so far. */
    public int tries() {
        return log.size();
    }

    /** Codes still consistent with every score. */
    public int candidatesLeft() {
        return candidates.length;
    }

    @Override
    public int toMove() {
        return over() ? 0 : 1;
    }

    @Override
    public boolean over() {
        return opened || log.size() >= MAX_TRIES;
    }

    @Override
    public int winner() {
        return opened ? 1 : 0;
    }

    @Override
    public String render() {
        StringBuilder sb = new StringBuilder();
        for (String l : log) {
            sb.append(l).append('\n');
        }
        String tail = "tries " + log.size();
        if (opened) {
            tail = "the lock opens!";
        } else if (over()) {
            tail = "the lock jams; code " + encode(secret);
        }
        return sb.append(tail).append('\n').toString();
    }

    @Override
    public String hint() {
        if (over()) {
            return "";
        }
        return encode(LockPegs.nextGuess(candidates));
    }
}