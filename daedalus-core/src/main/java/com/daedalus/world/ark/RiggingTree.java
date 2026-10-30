// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;
import java.util.PriorityQueue;

/**
 * G324 The Rigging Tree: the bosun lashes n numbered blocks (0..n-1) with n-1 lines into one
 * tree with no loops. Each rigging is logged as its Pruefer sequence (repeatedly strike the
 * lowest-numbered loose block and write down its neighbour), which is unique, so there are
 * exactly n^(n-2) riggings (Cayley).
 */
public final class RiggingTree {

    public static final String QUEST_ID = "q_rigging_tree";

    private RiggingTree() { }

    /** Pruefer sequence (length n-2) of a tree given as n-1 edges on blocks 0..n-1. */
    public static int[] encode(int n, int[][] edges) {
        if (n < 2 || edges.length != n - 1) {
            throw new IllegalArgumentException("a tree on " + n + " blocks needs " + (n - 1) + " lines");
        }
        int[] deg = new int[n];
        int[] xor = new int[n];
        for (int[] e : edges) {
            if (e.length != 2 || e[0] < 0 || e[1] < 0 || e[0] >= n || e[1] >= n || e[0] == e[1]) {
                throw new IllegalArgumentException("bad line " + Arrays.toString(e));
            }
            deg[e[0]]++;
            deg[e[1]]++;
            xor[e[0]] ^= e[1];
            xor[e[1]] ^= e[0];
        }
        PriorityQueue<Integer> leaves = new PriorityQueue<>();
        for (int v = 0; v < n; v++) {
            if (deg[v] == 0) {
                throw new IllegalArgumentException("not a tree");
            }
            if (deg[v] == 1) {
                leaves.add(v);
            }
        }
        int[] seq = new int[n - 2];
        for (int i = 0; i < n - 2; i++) {
            Integer leaf = leaves.poll();
            if (leaf == null) {
                throw new IllegalArgumentException("not a tree");
            }
            int p = xor[leaf];
            seq[i] = p;
            deg[leaf] = 0;
            xor[p] ^= leaf;
            deg[p]--;
            if (deg[p] == 1) {
                leaves.add(p);
            } else if (deg[p] == 0) {
                throw new IllegalArgumentException("not a tree");
            }
        }
        int left = 0;
        for (int v = 0; v < n; v++) {
            left += deg[v];
        }
        if (left != 2) {
            throw new IllegalArgumentException("not a tree");
        }
        return seq;
    }

    /** Rebuild the n-1 lines (each sorted, lower block first) from a Pruefer sequence. */
    public static int[][] decode(int[] seq) {
        int n = seq.length + 2;
        int[] deg = new int[n];
        Arrays.fill(deg, 1);
        for (int s : seq) {
            if (s < 0 || s >= n) {
                throw new IllegalArgumentException("block " + s + " out of range");
            }
            deg[s]++;
        }
        PriorityQueue<Integer> leaves = new PriorityQueue<>();
        for (int v = 0; v < n; v++) {
            if (deg[v] == 1) {
                leaves.add(v);
            }
        }
        int[][] edges = new int[n - 1][];
        int k = 0;
        for (int s : seq) {
            int leaf = leaves.remove();
            edges[k++] = new int[] {Math.min(leaf, s), Math.max(leaf, s)};
            deg[s]--;
            if (deg[s] == 1) {
                leaves.add(s);
            }
        }
        int a = leaves.remove();
        int b = leaves.remove();
        edges[k] = new int[] {Math.min(a, b), Math.max(a, b)};
        return edges;
    }

    /** Cayley's count n^(n-2) of riggings on n blocks (n up to 20). */
    public static long count(int n) {
        if (n < 1 || n > 20) {
            throw new IllegalArgumentException("n " + n);
        }
        if (n <= 2) {
            return 1;
        }
        long r = 1;
        for (int i = 0; i < n - 2; i++) {
            r *= n;
        }
        return r;
    }

    /** Quest q_rigging_tree: log the rigging's Pruefer sequence. */
    public static boolean quest(int n, int[][] edges, int[] answer) {
        return Arrays.equals(encode(n, edges), answer);
    }
}