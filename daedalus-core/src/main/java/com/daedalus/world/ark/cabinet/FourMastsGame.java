// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import com.daedalus.world.ark.FourMasts;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/**
 * Cabinet adapter for G432 The Four Masts (Tower of Hanoi with p masts, one player). A move is {@code from,to}
 * (1-based masts). The piece checks whole plans and gives the fewest count; it cannot suggest a move mid-game, so the
 * cabinet's hint is a breadth-first search here over sail positions (p^n states, kept small). Finished games are
 * checked with {@link FourMasts#valid}.
 */
public final class FourMastsGame implements ArkCabinetGame {

    /** Largest p^n state count the cabinet's hint search will take on. */
    public static final int MAX_HINT_STATES = 1 << 16;

    private final int n;
    private final int p;
    private final int[] mast;
    private final List<int[]> made = new ArrayList<>();

    /** Four sails on four masts. */
    public FourMastsGame() {
        this(4, 4);
    }

    /** n sails on p masts. */
    public FourMastsGame(int n, int p) {
        if (n < 1 || p < 3 || Math.pow(p, n) > MAX_HINT_STATES) {
            throw new IllegalArgumentException("too many states for the cabinet");
        }
        this.n = n;
        this.p = p;
        this.mast = new int[n];
    }

    @Override
    public String id() {
        return "masts";
    }

    @Override
    public String title() {
        return "The Four Masts";
    }

    @Override
    public String rules() {
        return "Type from,to (e.g. 1,4) to move a top sail. Never put a bigger sail on a smaller. All to the last mast.";
    }

    private static int top(int[] at, int m) {
        for (int s = 0; s < at.length; s++) {
            if (at[s] == m) {
                return s;
            }
        }
        return -1;
    }

    private List<int[]> movesFrom(int[] at) {
        List<int[]> out = new ArrayList<>();
        for (int a = 0; a < p; a++) {
            int s = top(at, a);
            if (s < 0) {
                continue;
            }
            for (int t = 0; t < p; t++) {
                int u = top(at, t);
                if (t != a && (u < 0 || u > s)) {
                    out.add(new int[] {a, t});
                }
            }
        }
        return out;
    }

    @Override
    public List<String> legalMoves() {
        List<String> out = new ArrayList<>();
        if (!over()) {
            for (int[] mv : movesFrom(mast)) {
                out.add((mv[0] + 1) + "," + (mv[1] + 1));
            }
        }
        return Collections.unmodifiableList(out);
    }

    @Override
    public boolean play(String move) {
        int[] ft = CabinetMoves.pair(move);
        int a = ft[0] - 1;
        int t = ft[1] - 1;
        for (int[] mv : over() ? List.<int[]>of() : movesFrom(mast)) {
            if (mv[0] == a && mv[1] == t) {
                mast[top(mast, a)] = t;
                made.add(mv);
                return true;
            }
        }
        return false;
    }

    /** Moves made so far. */
    public int movesMade() {
        return made.size();
    }

    /** True when the moves so far pass the piece's own plan checker. */
    public boolean checked() {
        return FourMasts.valid(n, p, made.toArray(new int[0][]));
    }

    @Override
    public int toMove() {
        return over() ? 0 : 1;
    }

    @Override
    public boolean over() {
        for (int m : mast) {
            if (m != p - 1) {
                return false;
            }
        }
        return true;
    }

    @Override
    public int winner() {
        return over() ? 1 : 0;
    }

    @Override
    public String render() {
        StringBuilder sb = new StringBuilder();
        for (int m = 0; m < p; m++) {
            sb.append(m + 1).append(" |");
            for (int s = n - 1; s >= 0; s--) {
                if (mast[s] == m) {
                    sb.append(' ').append(s + 1);
                }
            }
            sb.append('\n');
        }
        return sb.toString();
    }

    private int key(int[] at) {
        int k = 0;
        for (int s = n - 1; s >= 0; s--) {
            k = k * p + at[s];
        }
        return k;
    }

    @Override
    public String hint() {
        if (over()) {
            return "";
        }
        int states = (int) Math.pow(p, n);
        int[] firstMove = new int[states];
        Arrays.fill(firstMove, -1);
        boolean[] seen = new boolean[states];
        seen[key(mast)] = true;
        List<int[]> first = movesFrom(mast);
        ArrayDeque<int[]> q = new ArrayDeque<>();
        for (int i = 0; i < first.size(); i++) {
            int[] at = mast.clone();
            at[top(at, first.get(i)[0])] = first.get(i)[1];
            int k = key(at);
            if (!seen[k]) {
                seen[k] = true;
                firstMove[k] = i;
                q.add(at);
            }
        }
        int[] goal = new int[n];
        Arrays.fill(goal, p - 1);
        int gk = key(goal);
        while (!q.isEmpty()) {
            int[] at = q.poll();
            int k = key(at);
            if (k == gk) {
                int[] mv = first.get(firstMove[k]);
                return (mv[0] + 1) + "," + (mv[1] + 1);
            }
            for (int[] mv : movesFrom(at)) {
                int[] nx = at.clone();
                nx[top(nx, mv[0])] = mv[1];
                int nk = key(nx);
                if (!seen[nk]) {
                    seen[nk] = true;
                    firstMove[nk] = firstMove[k];
                    q.add(nx);
                }
            }
        }
        return legalMoves().get(0);
    }
}
