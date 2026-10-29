// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import com.daedalus.world.ark.GalleyStack;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Solo cabinet adapter for G428 The Galley Stack (pancake flips); the exact solver lives in {@link GalleyStack}. */
public final class GalleyStackGame implements ArkCabinetGame {

    /** The starting stack, top first. */
    private static final int[] STARTER = {3, 1, 4, 0, 5, 2};

    private int[] stack;
    private int flips;

    /** The cabinet's six-plate starter stack. */
    public GalleyStackGame() {
        this(STARTER);
    }

    /** A stack of 2 to {@link GalleyStack#MAX_EXACT} plates, a permutation of 0..n-1 with index 0 on top. */
    public GalleyStackGame(int... start) {
        if (start == null || start.length < 2 || start.length > GalleyStack.MAX_EXACT) {
            throw new IllegalArgumentException("2 to " + GalleyStack.MAX_EXACT + " plates");
        }
        this.stack = GalleyStack.flip(start.clone(), 1);
    }

    @Override
    public String id() {
        return "galley";
    }

    @Override
    public String title() {
        return "The Galley Stack";
    }

    @Override
    public String rules() {
        return "Type k to flip the top k plates. Stack them smallest on top in the fewest flips.";
    }

    @Override
    public List<String> legalMoves() {
        List<String> out = new ArrayList<>();
        if (!over()) {
            for (int k = 2; k <= stack.length; k++) {
                out.add(Integer.toString(k));
            }
        }
        return Collections.unmodifiableList(out);
    }

    @Override
    public boolean play(String move) {
        int k = CabinetMoves.number(move);
        if (over() || k < 2 || k > stack.length) {
            return false;
        }
        stack = GalleyStack.flip(stack, k);
        flips++;
        return true;
    }

    /** Flips made so far. */
    public int flips() {
        return flips;
    }

    /** Fewest flips still needed from here. */
    public int fewestLeft() {
        return GalleyStack.fewest(stack).length;
    }

    @Override
    public int toMove() {
        return over() ? 0 : 1;
    }

    @Override
    public boolean over() {
        return GalleyStack.sorted(stack);
    }

    @Override
    public int winner() {
        return over() ? 1 : 0;
    }

    @Override
    public String render() {
        StringBuilder sb = new StringBuilder();
        for (int p : stack) {
            sb.append(' ').append("=".repeat(2 * p + 1)).append('\n');
        }
        return sb.append("flips ").append(flips).append(over() ? " - stacked!" : "").append('\n').toString();
    }

    @Override
    public String hint() {
        if (over()) {
            return "";
        }
        return Integer.toString(GalleyStack.fewest(stack)[0]);
    }
}