// SPDX-License-Identifier: MIT

package com.daedalus.graph;

/**
 * The engine's graph seam — the abstraction that lets Daedalus route over <em>any</em> topology,
 * not just a rectangular maze grid (see {@code docs/adr/ADR-001-graph-engine-seam.md}).
 *
 * <p>Nodes are dense integer ids in {@code [0, nodeCount())}, so all traversal state lives in flat
 * arrays. That is deliberate and measured: replacing {@code Point}-keyed hash collections with
 * cell-id arrays made Dijkstra and A* 1.42–1.72x faster, because hashing and boxing — not the
 * priority queue — dominated the search loop.
 *
 * <p>Adjacency is exposed in an <b>allocation-free</b> form. {@link #neighbors(int, int[])} fills a
 * caller-owned buffer instead of returning a collection, so a hot loop allocates nothing at all;
 * size the buffer once with {@link #maxDegree()}. This is the same adjacency-list model as CLRS
 * Ch. 22, just without a per-call {@code List}.
 *
 * <p>Implementations are free to be live views over another structure ({@link MazeGraph}) or
 * materialised snapshots ({@link CsrGraph}). A view reflects later mutations of its backing
 * object; a snapshot does not. Each implementation states which it is.
 */
public interface Graph {

    /** Number of nodes; valid ids are {@code [0, nodeCount())}. */
    int nodeCount();

    /** Upper bound on any node's degree — the size a {@link #neighbors} buffer needs. */
    int maxDegree();

    /**
     * Write {@code node}'s neighbours into {@code out} and return how many were written.
     *
     * @param out caller-owned buffer of at least {@link #maxDegree()} entries
     * @return the degree of {@code node}
     */
    int neighbors(int node, int[] out);

    /**
     * Cost of traversing from {@code from} to the adjacent node {@code to}. Must be non-negative
     * for Dijkstra and A* to remain correct. Uniform-cost graphs return {@code 1.0}.
     */
    double edgeWeight(int from, int to);
}
