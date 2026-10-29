// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import com.daedalus.world.ark.SignalCube;
import java.util.Arrays;
import java.util.List;

/**
 * Cabinet adapter for G435 The Signal Cube (pocket cube, one player); turns, the solved test and the optimal solve
 * live in {@link SignalCube}. A move is one turn name such as {@code R}, {@code U2} or {@code F'}.
 */
public final class SignalCubeGame implements ArkCabinetGame {

    /** The cabinet's starter scramble. */
    public static final String STARTER = "R U F' R2 U'";

    private int[] state;
    private int turnsMade;

    /** Starts from {@link #STARTER}. */
    public SignalCubeGame() {
        this(STARTER);
    }

    /** Starts from the given scramble. */
    public SignalCubeGame(String scramble) {
        this.state = SignalCube.apply(SignalCube.solvedState(), scramble);
    }

    @Override
    public String id() {
        return "cube";
    }

    @Override
    public String title() {
        return "The Signal Cube";
    }

    @Override
    public String rules() {
        return "Type a turn: R, U or F, add 2 for a half turn or ' to turn back. Solve the cube.";
    }

    @Override
    public List<String> legalMoves() {
        return over() ? List.of() : List.copyOf(SignalCube.turns());
    }

    @Override
    public boolean play(String move) {
        if (over() || move == null || !SignalCube.turns().contains(move.trim())) {
            return false;
        }
        state = SignalCube.apply(state, move.trim());
        turnsMade++;
        return true;
    }

    /** Turns made so far. */
    public int turnsMade() {
        return turnsMade;
    }

    /** Fewest half-turn-metric turns still needed. */
    public int distance() {
        return SignalCube.distance(state, false);
    }

    @Override
    public int toMove() {
        return over() ? 0 : 1;
    }

    @Override
    public boolean over() {
        return SignalCube.solved(state);
    }

    @Override
    public int winner() {
        return over() ? 1 : 0;
    }

    @Override
    public String render() {
        return "cube " + Arrays.toString(state) + "\n" + (over() ? "solved" : distance() + " turns from solved") + "\n";
    }

    @Override
    public String hint() {
        if (over()) {
            return "";
        }
        String s = SignalCube.solve(state).trim();
        int sp = s.indexOf(' ');
        return sp < 0 ? s : s.substring(0, sp);
    }
}
