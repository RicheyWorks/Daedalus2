// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Optional;
import java.util.SplittableRandom;

/**
 * Chain Weld (contest gap G315): each link joins a socket of one size to a socket of another, in one direction only.
 * Weld every link into one unbroken chain, using each exactly once, or show it cannot be done.
 *
 * <p>The tool is plain: {@link #eulerPath} is Hierholzer's algorithm with an explicit stack on a directed multigraph,
 * after in/out degree checks, returning link indices in chain order. Any project can use it for route-every-edge
 * puzzles, sequence assembly, or one-stroke drawings.
 */
public final class ChainWeld {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_chain_weld";

    /** How a weld went. */
    public enum Grade { WELDED, SNAPPED }

    private ChainWeld() {
    }

    /** {@code m} seeded links over sockets 0..sockets-1, each {from, to}. Same seed, same links. */
    public static int[][] links(long seed, int sockets, int m) {
        if (sockets < 1 || m < 0) {
            throw new IllegalArgumentException("need sockets >= 1 and m >= 0");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[][] e = new int[m][2];
        for (int[] x : e) {
            x[0] = r.nextInt(sockets);
            x[1] = r.nextInt(sockets);
        }
        return e;
    }

    /** Link indices in an order that forms one chain, or empty if none exists. An empty set gives an empty chain. */
    public static Optional<int[]> eulerPath(int sockets, int[][] links) {
        int m = links.length;
        int[] out = new int[sockets];
        int[] in = new int[sockets];
        for (int[] e : links) {
            if (e[0] < 0 || e[0] >= sockets || e[1] < 0 || e[1] >= sockets) {
                throw new IllegalArgumentException("socket out of range");
            }
            out[e[0]]++;
            in[e[1]]++;
        }
        if (m == 0) {
            return Optional.of(new int[0]);
        }
        int start = links[0][0];
        int plus = 0;
        int minus = 0;
        for (int v = 0; v < sockets; v++) {
            int d = out[v] - in[v];
            if (d == 1) {
                plus++;
                start = v;
            } else if (d == -1) {
                minus++;
            } else if (d != 0) {
                return Optional.empty();
            }
        }
        if (plus > 1 || minus > 1 || plus != minus) {
            return Optional.empty();
        }
        int[] head = new int[sockets + 1];
        for (int[] e : links) {
            head[e[0] + 1]++;
        }
        for (int v = 0; v < sockets; v++) {
            head[v + 1] += head[v];
        }
        int[] adj = new int[m];
        int[] fill = head.clone();
        for (int i = 0; i < m; i++) {
            adj[fill[links[i][0]]++] = i;
        }
        int[] ptr = head.clone();
        int[] stackV = new int[m + 1];
        int[] stackE = new int[m + 1];
        int[] path = new int[m];
        int top = 0;
        int len = m;
        stackV[0] = start;
        stackE[0] = -1;
        while (top >= 0) {
            int v = stackV[top];
            if (ptr[v] < head[v + 1]) {
                int e = adj[ptr[v]++];
                top++;
                stackV[top] = links[e][1];
                stackE[top] = e;
            } else {
                if (stackE[top] >= 0) {
                    path[--len] = stackE[top];
                }
                top--;
            }
        }
        return len == 0 ? Optional.of(path) : Optional.empty();
    }

    /** True if the order uses every link once and each link starts where the previous one ended. */
    public static boolean isChain(int[][] links, int[] order) {
        if (order.length != links.length) {
            return false;
        }
        boolean[] used = new boolean[links.length];
        for (int k = 0; k < order.length; k++) {
            int e = order[k];
            if (e < 0 || e >= links.length || used[e]) {
                return false;
            }
            used[e] = true;
            if (k > 0 && links[order[k - 1]][1] != links[e][0]) {
                return false;
            }
        }
        return true;
    }

    /** WELDED for a valid full chain, or for a null claim when no chain exists. */
    public static Grade grade(int sockets, int[][] links, int[] claimed) {
        boolean possible = eulerPath(sockets, links).isPresent();
        if (claimed == null) {
            return possible ? Grade.SNAPPED : Grade.WELDED;
        }
        return isChain(links, claimed) ? Grade.WELDED : Grade.SNAPPED;
    }

    /** The Forgemaster's line for a weld. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case WELDED -> "Forgemaster: every link in, not one left on the bench. That chain will hold.";
            case SNAPPED -> "Forgemaster: the chain breaks there. Lay the links out and trace them again.";
        };
    }
}
