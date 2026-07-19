// SPDX-License-Identifier: MIT

package com.daedalus.graph;

import java.util.ArrayList;
import java.util.List;

/**
 * A {@link Graph} built from caller-supplied edges — the entry point for consumers that bring
 * their own topology (a service mesh, a rack layout, a LoadBalancerPro lab fixture) rather than a
 * maze.
 *
 * <p>Stored in compressed-sparse-row form: one {@code offsets} array indexed by node, and flat
 * {@code targets} / {@code weights} arrays holding every adjacency back to back. That is the dense
 * form of CLRS Ch. 22's adjacency list — same asymptotics, contiguous memory, no per-node objects.
 *
 * <p>This is a <b>snapshot</b>: edges are fixed at build time. Rebuild to change the topology.
 * Edge weights may be updated in place through {@link #setEdgeWeight} so live signals (latency,
 * load) can move without rebuilding the structure — the shape stays put, only the costs change.
 *
 * <p>Undirected use is supported by adding both directions; {@link Builder#addUndirected} does it
 * for you.
 */
public final class CsrGraph implements Graph {

    private final int[] offsets;
    private final int[] targets;
    private final double[] weights;
    private final int maxDegree;

    private CsrGraph(int[] offsets, int[] targets, double[] weights, int maxDegree) {
        this.offsets = offsets;
        this.targets = targets;
        this.weights = weights;
        this.maxDegree = maxDegree;
    }

    public static Builder builder(int nodeCount) {
        return new Builder(nodeCount);
    }

    @Override
    public int nodeCount() {
        return offsets.length - 1;
    }

    @Override
    public int maxDegree() {
        return maxDegree;
    }

    @Override
    public int neighbors(int node, int[] out) {
        int from = offsets[node];
        int count = offsets[node + 1] - from;
        System.arraycopy(targets, from, out, 0, count);
        return count;
    }

    @Override
    public double edgeWeight(int from, int to) {
        for (int i = offsets[from]; i < offsets[from + 1]; i++) {
            if (targets[i] == to) {
                return weights[i];
            }
        }
        throw new IllegalArgumentException("No edge " + from + " -> " + to);
    }

    /**
     * Update a live edge cost without rebuilding — the hook for feeding real latency or load into
     * an existing topology.
     */
    public void setEdgeWeight(int from, int to, double weight) {
        for (int i = offsets[from]; i < offsets[from + 1]; i++) {
            if (targets[i] == to) {
                weights[i] = weight;
                return;
            }
        }
        throw new IllegalArgumentException("No edge " + from + " -> " + to);
    }

    /** Accumulates edges, then packs them into CSR form. */
    public static final class Builder {
        private final int nodeCount;
        private final List<int[]> edges = new ArrayList<>();
        private final List<Double> edgeWeights = new ArrayList<>();

        private Builder(int nodeCount) {
            if (nodeCount < 0) {
                throw new IllegalArgumentException("nodeCount must be >= 0, got " + nodeCount);
            }
            this.nodeCount = nodeCount;
        }

        /** One directed edge. */
        public Builder addEdge(int from, int to, double weight) {
            checkNode(from);
            checkNode(to);
            if (weight < 0.0) {
                throw new IllegalArgumentException("Edge weights must be non-negative, got " + weight);
            }
            edges.add(new int[] {from, to});
            edgeWeights.add(weight);
            return this;
        }

        /** Both directions of an undirected link. */
        public Builder addUndirected(int a, int b, double weight) {
            return addEdge(a, b, weight).addEdge(b, a, weight);
        }

        public CsrGraph build() {
            int[] degree = new int[nodeCount];
            for (int[] edge : edges) {
                degree[edge[0]]++;
            }
            int[] offsets = new int[nodeCount + 1];
            int maxDegree = 0;
            for (int v = 0; v < nodeCount; v++) {
                offsets[v + 1] = offsets[v] + degree[v];
                maxDegree = Math.max(maxDegree, degree[v]);
            }

            int[] targets = new int[edges.size()];
            double[] weights = new double[edges.size()];
            int[] cursor = new int[nodeCount];
            for (int i = 0; i < edges.size(); i++) {
                int[] edge = edges.get(i);
                int slot = offsets[edge[0]] + cursor[edge[0]]++;
                targets[slot] = edge[1];
                weights[slot] = edgeWeights.get(i);
            }
            return new CsrGraph(offsets, targets, weights, maxDegree);
        }

        private void checkNode(int node) {
            if (node < 0 || node >= nodeCount) {
                throw new IllegalArgumentException("Node " + node + " outside [0, " + nodeCount + ")");
            }
        }
    }
}
