// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * G435 The Signal Cube: the lookout's 2x2x2 signal cube (the pocket cube) with the
 * left-down-back corner held still, so only R, U and F turns are needed. Corner move tables are
 * built from sticker rotations. A state is 14 ints: the corner at each of the 7 moving places,
 * then each place's twist (which sticker slot holds the corner's up/down sticker). Gives
 * scrambles, the exact distance and an optimal solve from a full breadth-first table, the
 * number of states and God's number in half turns and in quarter turns.
 */
public final class SignalCube {

    public static final String QUEST_ID = "q_signal_cube";
    private static final String[] TURNS = {"R", "R2", "R'", "U", "U2", "U'", "F", "F2", "F'"};
    private static final int PLACES = 7;
    private static final int SIZE = 5040 * 2187;
    private static final int[][] POS = new int[PLACES][];
    private static final int[][] TO = new int[9][PLACES];
    private static final int[][][] SLOT = new int[9][PLACES][3];
    private static final int[] SLOT_AXIS = {1, 0, 2};
    private static byte[] halfTable;
    private static byte[] quarterTable;

    static {
        int k = 0;
        for (int x = -1; x <= 1; x += 2) {
            for (int y = -1; y <= 1; y += 2) {
                for (int z = -1; z <= 1; z += 2) {
                    if (x + y + z != -3) {
                        POS[k++] = new int[] {x, y, z};
                    }
                }
            }
        }
        for (int axis = 0; axis < 3; axis++) {
            for (int q = 1; q <= 3; q++) {
                int mv = axis * 3 + q - 1;
                for (int p = 0; p < PLACES; p++) {
                    int[] v = POS[p].clone();
                    int[] slotAxis = SLOT_AXIS.clone();
                    if (v[axis] == 1) {
                        for (int t = 0; t < q; t++) {
                            v = turn(v, axis);
                            for (int s = 0; s < 3; s++) {
                                slotAxis[s] = turnAxis(slotAxis[s], axis);
                            }
                        }
                    }
                    int dest = find(v);
                    TO[mv][p] = dest;
                    for (int s = 0; s < 3; s++) {
                        SLOT[mv][p][s] = indexOf(slotAxis[s]);
                    }
                }
            }
        }
    }

    private SignalCube() { }

    /** The nine turn names in move-table order. */
    public static List<String> turns() {
        return List.of(TURNS);
    }

    private static int[] turn(int[] v, int a) {
        int b = (a + 1) % 3;
        int c = (a + 2) % 3;
        int[] w = v.clone();
        w[b] = -v[c];
        w[c] = v[b];
        return w;
    }

    private static int turnAxis(int n, int a) {
        int b = (a + 1) % 3;
        int c = (a + 2) % 3;
        if (n == b) {
            return c;
        }
        return n == c ? b : n;
    }

    private static int indexOf(int axis) {
        for (int s = 0; s < 3; s++) {
            if (SLOT_AXIS[s] == axis) {
                return s;
            }
        }
        throw new IllegalStateException("axis " + axis);
    }

    private static int find(int[] v) {
        for (int p = 0; p < PLACES; p++) {
            if (Arrays.equals(POS[p], v)) {
                return p;
            }
        }
        throw new IllegalStateException("fixed corner moved");
    }

    /** The solved cube. */
    public static int[] solvedState() {
        int[] s = new int[2 * PLACES];
        for (int p = 0; p < PLACES; p++) {
            s[p] = p;
        }
        return s;
    }

    private static void check(int[] s) {
        if (s == null || s.length != 2 * PLACES) {
            throw new IllegalArgumentException("state must have 14 entries");
        }
        boolean[] seen = new boolean[PLACES];
        for (int p = 0; p < PLACES; p++) {
            if (s[p] < 0 || s[p] >= PLACES || seen[s[p]] || s[PLACES + p] < 0 || s[PLACES + p] > 2) {
                throw new IllegalArgumentException("bad cube state");
            }
            seen[s[p]] = true;
        }
    }

    private static int[] turnState(int[] s, int mv) {
        int[] out = new int[2 * PLACES];
        for (int p = 0; p < PLACES; p++) {
            int dest = TO[mv][p];
            out[dest] = s[p];
            out[PLACES + dest] = SLOT[mv][p][s[PLACES + p]];
        }
        return out;
    }

    /** Applies turns written like "R U2 F'" (blank string allowed). */
    public static int[] apply(int[] state, String turns) {
        check(state);
        int[] s = state.clone();
        for (int mv : parse(turns)) {
            s = turnState(s, mv);
        }
        return s;
    }

    private static int[] parse(String turns) {
        if (turns == null) {
            throw new IllegalArgumentException("turns must not be null");
        }
        String t = turns.trim();
        if (t.isEmpty()) {
            return new int[0];
        }
        String[] parts = t.split("\\s+");
        int[] out = new int[parts.length];
        for (int i = 0; i < parts.length; i++) {
            out[i] = List.of(TURNS).indexOf(parts[i]);
            if (out[i] < 0) {
                throw new IllegalArgumentException("unknown turn: " + parts[i]);
            }
        }
        return out;
    }

    /** True when every corner is home and untwisted. */
    public static boolean solved(int[] s) {
        check(s);
        return Arrays.equals(s, solvedState());
    }

    private static int rank(int[] s) {
        int r = 0;
        for (int i = 0; i < PLACES; i++) {
            int smaller = 0;
            for (int j = i + 1; j < PLACES; j++) {
                if (s[j] < s[i]) {
                    smaller++;
                }
            }
            r = r * (PLACES - i) + smaller;
        }
        int o = 0;
        for (int i = 0; i < PLACES; i++) {
            o = o * 3 + s[PLACES + i];
        }
        return r * 2187 + o;
    }

    private static synchronized byte[] table(boolean quarter) {
        if (quarter && quarterTable != null) {
            return quarterTable;
        }
        if (!quarter && halfTable != null) {
            return halfTable;
        }
        byte[] dist = new byte[SIZE];
        Arrays.fill(dist, (byte) -1);
        List<int[]> frontier = new ArrayList<>();
        frontier.add(solvedState());
        dist[rank(solvedState())] = 0;
        for (int depth = 0; !frontier.isEmpty(); depth++) {
            List<int[]> next = new ArrayList<>();
            for (int[] s : frontier) {
                for (int mv = 0; mv < 9; mv++) {
                    if (quarter && mv % 3 == 1) {
                        continue;
                    }
                    int[] t = turnState(s, mv);
                    int r = rank(t);
                    if (dist[r] < 0) {
                        dist[r] = (byte) (depth + 1);
                        next.add(t);
                    }
                }
            }
            frontier = next;
        }
        if (quarter) {
            quarterTable = dist;
        } else {
            halfTable = dist;
        }
        return dist;
    }

    /** Fewest turns to solve, counting a half turn as one (quarter = false) or two quarters. */
    public static int distance(int[] s, boolean quarter) {
        check(s);
        int d = table(quarter)[rank(s)];
        if (d < 0) {
            throw new IllegalArgumentException("state cannot be reached by turning");
        }
        return d;
    }

    /** An optimal solve in half-turn metric, as a turn string. */
    public static String solve(int[] state) {
        byte[] t = table(false);
        int[] s = state.clone();
        StringBuilder sb = new StringBuilder();
        for (int d = distance(s, false); d > 0; d--) {
            for (int mv = 0; mv < 9; mv++) {
                int[] n = turnState(s, mv);
                if (t[rank(n)] == d - 1) {
                    s = n;
                    sb.append(sb.length() == 0 ? "" : " ").append(TURNS[mv]);
                    break;
                }
            }
        }
        return sb.toString();
    }

    /** Number of states reachable by turning. */
    public static int stateCount() {
        int n = 0;
        for (byte b : table(false)) {
            n += b >= 0 ? 1 : 0;
        }
        return n;
    }

    /** Most turns any state needs (God's number) in the chosen metric. */
    public static int godsNumber(boolean quarter) {
        int best = 0;
        for (byte b : table(quarter)) {
            best = Math.max(best, b);
        }
        return best;
    }

    /** Quest q_signal_cube: the lookout names the fewest half-turn moves to solve this scramble. */
    public static boolean quest(String scramble, int answer) {
        return distance(apply(solvedState(), scramble), false) == answer;
    }
}