// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.Optional;
import java.util.SplittableRandom;

/**
 * Damper Pact (contest gap G318): each furnace damper is OPEN or SHUT, and the guild posts two-damper rules. Find a
 * setting that honours every rule or prove none exists.
 *
 * <p>The tool is plain: {@link #solve} is 2-SAT. A rule is a clause {@code {a, b}} meaning "a or b", where literal
 * {@code +k} is damper k-1 OPEN and {@code -k} is damper k-1 SHUT. It builds the implication graph, finds strongly
 * connected components with an iterative Kosaraju pass, and reads the setting off component order. Any project can use
 * it for paired constraints.
 */
public final class DamperPact {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_damper_pact";

    /** How a setting went. */
    public enum Grade { HONOURED, BROKEN }

    private DamperPact() {
    }

    /** {@code m} seeded rules over {@code n} dampers. Same seed, same pact. */
    public static int[][] rules(long seed, int n, int m) {
        if (n < 1 || m < 0) {
            throw new IllegalArgumentException("need n >= 1 and m >= 0");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[][] c = new int[m][2];
        for (int[] x : c) {
            x[0] = (1 + r.nextInt(n)) * (r.nextBoolean() ? 1 : -1);
            x[1] = (1 + r.nextInt(n)) * (r.nextBoolean() ? 1 : -1);
        }
        return c;
    }

    private static int node(int lit, int n) {
        int k = Math.abs(lit);
        if (lit == 0 || k > n) {
            throw new IllegalArgumentException("literal out of range: " + lit);
        }
        return 2 * (k - 1) + (lit > 0 ? 0 : 1);
    }

    /** A setting (true = OPEN) honouring every rule, or empty if none exists. */
    public static Optional<boolean[]> solve(int n, int[][] clauses) {
        int v = 2 * n;
        int m = clauses.length;
        int[] from = new int[2 * m];
        int[] to = new int[2 * m];
        for (int i = 0; i < m; i++) {
            int a = node(clauses[i][0], n);
            int b = node(clauses[i][1], n);
            from[2 * i] = a ^ 1;
            to[2 * i] = b;
            from[2 * i + 1] = b ^ 1;
            to[2 * i + 1] = a;
        }
        int[][] g = csr(v, from, to);
        int[][] rg = csr(v, to, from);
        int[] order = new int[v];
        int cnt = 0;
        boolean[] seen = new boolean[v];
        int[] stack = new int[v];
        int[] it = new int[v];
        for (int s = 0; s < v; s++) {
            if (seen[s]) {
                continue;
            }
            int top = 0;
            stack[0] = s;
            seen[s] = true;
            it[s] = g[0][s];
            while (top >= 0) {
                int x = stack[top];
                if (it[x] < g[0][x + 1]) {
                    int y = g[1][it[x]++];
                    if (!seen[y]) {
                        seen[y] = true;
                        it[y] = g[0][y];
                        stack[++top] = y;
                    }
                } else {
                    order[cnt++] = x;
                    top--;
                }
            }
        }
        int[] comp = new int[v];
        Arrays.fill(comp, -1);
        int c = 0;
        for (int k = v - 1; k >= 0; k--) {
            int s = order[k];
            if (comp[s] >= 0) {
                continue;
            }
            int top = 0;
            stack[0] = s;
            comp[s] = c;
            while (top >= 0) {
                int x = stack[top--];
                for (int e = rg[0][x]; e < rg[0][x + 1]; e++) {
                    int y = rg[1][e];
                    if (comp[y] < 0) {
                        comp[y] = c;
                        stack[++top] = y;
                    }
                }
            }
            c++;
        }
        boolean[] open = new boolean[n];
        for (int i = 0; i < n; i++) {
            if (comp[2 * i] == comp[2 * i + 1]) {
                return Optional.empty();
            }
            open[i] = comp[2 * i] > comp[2 * i + 1];
        }
        return Optional.of(open);
    }

    private static int[][] csr(int v, int[] from, int[] to) {
        int[] head = new int[v + 1];
        for (int f : from) {
            head[f + 1]++;
        }
        for (int i = 0; i < v; i++) {
            head[i + 1] += head[i];
        }
        int[] fill = head.clone();
        int[] adj = new int[from.length];
        for (int e = 0; e < from.length; e++) {
            adj[fill[from[e]]++] = to[e];
        }
        return new int[][] {head, adj};
    }

    /** True if the setting satisfies every rule. */
    public static boolean honours(boolean[] open, int[][] clauses) {
        for (int[] cl : clauses) {
            if (!lit(open, cl[0]) && !lit(open, cl[1])) {
                return false;
            }
        }
        return true;
    }

    private static boolean lit(boolean[] open, int l) {
        boolean v = open[Math.abs(l) - 1];
        return l > 0 ? v : !v;
    }

    /** HONOURED for a valid setting, or for a null claim when no setting exists. */
    public static Grade grade(int n, int[][] clauses, boolean[] claimed) {
        if (claimed == null) {
            return solve(n, clauses).isPresent() ? Grade.BROKEN : Grade.HONOURED;
        }
        return claimed.length == n && honours(claimed, clauses) ? Grade.HONOURED : Grade.BROKEN;
    }

    /** The Forgemaster's line for a setting. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case HONOURED -> "Forgemaster: every rule kept, every damper where it should be. The guild is satisfied.";
            case BROKEN -> "Forgemaster: that setting breaks the pact. Trace what each damper forces and try again.";
        };
    }
}
