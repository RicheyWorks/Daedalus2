// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import com.daedalus.world.ark.MeasuringCasks;
import com.daedalus.world.ark.MeasuringCasks.Move;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Solo cabinet adapter for G268 The Measuring Casks (water jugs); pouring rules and the fewest-move plan live in
 * {@link MeasuringCasks}. The live levels are always replayed through {@link MeasuringCasks#play}. The hint follows the
 * piece's plan while the player stays on it; off the plan it empties the casks back to the start and picks the plan up
 * again. The game is won when either cask holds exactly the target.
 */
public final class MeasuringCasksGame implements ArkCabinetGame {

    private static final List<Move> MOVES = List.of(Move.values());
    private static final List<String> TOKENS = List.of("fillA", "fillB", "emptyA", "emptyB", "pourAB", "pourBA");

    private final int capA;
    private final int capB;
    private final int target;
    private final List<Move> line;
    private final List<Move> history = new ArrayList<>();
    private int levelA;
    private int levelB;
    private int step;
    private boolean onLine = true;

    /** The classic puzzle: casks of 3 and 5 litres, measure 4. */
    public MeasuringCasksGame() {
        this(3, 5, 4);
    }

    /** Casks of a and b litres and a reachable target 1..max(a, b). */
    public MeasuringCasksGame(int a, int b, int c) {
        if (c < 1 || !MeasuringCasks.solvable(a, b, c)) {
            throw new IllegalArgumentException("target cannot be measured");
        }
        this.capA = a;
        this.capB = b;
        this.target = c;
        this.line = List.copyOf(MeasuringCasks.plan(a, b, c));
    }

    @Override
    public String id() {
        return "casks";
    }

    @Override
    public String title() {
        return "The Measuring Casks";
    }

    @Override
    public String rules() {
        return "Type fillA, fillB, emptyA, emptyB, pourAB or pourBA. Get exactly " + target
            + " litres into either cask to win.";
    }

    private int[] levelsAfter(Move m) {
        List<Move> next = new ArrayList<>(history);
        next.add(m);
        return MeasuringCasks.play(capA, capB, next);
    }

    @Override
    public List<String> legalMoves() {
        List<String> out = new ArrayList<>();
        if (!over()) {
            for (int i = 0; i < MOVES.size(); i++) {
                int[] l = levelsAfter(MOVES.get(i));
                if (l[0] != levelA || l[1] != levelB) {
                    out.add(TOKENS.get(i));
                }
            }
        }
        return Collections.unmodifiableList(out);
    }

    @Override
    public boolean play(String move) {
        if (move == null || over()) {
            return false;
        }
        for (int i = 0; i < MOVES.size(); i++) {
            if (TOKENS.get(i).equalsIgnoreCase(move.trim())) {
                Move m = MOVES.get(i);
                int[] l = levelsAfter(m);
                if (l[0] == levelA && l[1] == levelB) {
                    return false;
                }
                if (onLine && step < line.size() && line.get(step) == m) {
                    step++;
                } else {
                    onLine = false;
                }
                history.add(m);
                levelA = l[0];
                levelB = l[1];
                if (levelA == 0 && levelB == 0) {
                    onLine = true;
                    step = 0;
                }
                return true;
            }
        }
        return false;
    }

    /** Litres in cask A. */
    public int levelA() {
        return levelA;
    }

    /** Litres in cask B. */
    public int levelB() {
        return levelB;
    }

    /** Moves played so far. */
    public int moves() {
        return history.size();
    }

    /** Fewest moves for the whole puzzle from empty casks, from the piece's plan. */
    public int fewest() {
        return line.size();
    }

    @Override
    public int toMove() {
        return over() ? 0 : 1;
    }

    @Override
    public boolean over() {
        return levelA == target || levelB == target;
    }

    @Override
    public int winner() {
        return over() ? 1 : 0;
    }

    @Override
    public String render() {
        String s = "cask A " + levelA + "/" + capA + "   cask B " + levelB + "/" + capB + "   target " + target + "\n";
        return s + (over() ? "measured " + target + " litres in " + moves() + " moves!" : "moves " + moves()) + "\n";
    }

    @Override
    public String hint() {
        if (over()) {
            return "";
        }
        if (onLine && step < line.size()) {
            return TOKENS.get(line.get(step).ordinal());
        }
        return levelA > 0 ? TOKENS.get(Move.EMPTY_A.ordinal()) : TOKENS.get(Move.EMPTY_B.ordinal());
    }
}
