// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Bipartite b-matching via max-flow — CLRS Ch. 26, the selection question A* cannot answer.
 *
 * <p>Assign a batch of requests to servers under per-server capacity. Each request takes at
 * most one server; each server takes at most its capacity. That is the principled form of
 * "least connections" when you are placing many requests at once rather than one at a time,
 * and it is the algorithm whose shape matches a load-balancer {@code RoutingStrategy}
 * (ADR-001 appendix 3). The LoadBalancerPro seam that would host it is still closed; this
 * class is the offline primitive the topology example can already run.
 *
 * <p>Reduction: source → each request (cap 1), request → each eligible server (cap 1),
 * server → sink (cap = that server's capacity). Edmonds-Karp; BFS follows increasing
 * server index, so the assignment is deterministic.
 *
 * <p>Greedy first-fit is not a substitute. A request that can go to either of two servers
 * will take the first and strand the request that can only use that one. Max-flow does
 * not. The test that pins this is written against that fixture.
 */
public final class BipartiteMatching {

    private BipartiteMatching() {
    }

    /** One request placed on one server, both as caller-facing indexes. */
    public record Assignment(int request, int server) {
    }

    /**
     * @param pairs              request→server placements, sorted by request index
     * @param unmatchedRequests  requests that received no server
     */
    public record Matching(List<Assignment> pairs, int unmatchedRequests) {
        public Matching {
            pairs = List.copyOf(pairs);
        }
    }

    /**
     * Maze reading: assign request cells to facilities. A request may use a facility only
     * when a route of at most {@code maxHops} exists. Per-facility capacity is uniform.
     */
    public record Placement(List<Point> requests, List<Point> facilities,
                            List<Assigned> pairs, int unmatchedRequests) {
        public Placement {
            requests = List.copyOf(requests);
            facilities = List.copyOf(facilities);
            pairs = List.copyOf(pairs);
        }
    }

    public record Assigned(Point request, Point facility) {
    }

    /**
     * Assign {@code nRequests} to {@code nServers}. {@code eligible[i][j]} is whether
     * request {@code i} may use server {@code j}. {@code capacity[j]} is how many requests
     * server {@code j} can take.
     */
    public static Matching assign(int nRequests, int nServers, int[] capacity, boolean[][] eligible) {
        if (nRequests < 0 || nServers < 0) {
            throw new IllegalArgumentException("request and server counts must be >= 0");
        }
        if (capacity == null || capacity.length != nServers) {
            throw new IllegalArgumentException("capacity must have one entry per server");
        }
        if (eligible == null || eligible.length != nRequests) {
            throw new IllegalArgumentException("eligible must be nRequests × nServers");
        }
        for (int j = 0; j < nServers; j++) {
            if (capacity[j] < 0) {
                throw new IllegalArgumentException("server capacity must be >= 0, got " + capacity[j]);
            }
        }
        for (int i = 0; i < nRequests; i++) {
            if (eligible[i] == null || eligible[i].length != nServers) {
                throw new IllegalArgumentException("eligible[" + i + "] must have nServers columns");
            }
        }
        if (nRequests == 0) {
            return new Matching(List.of(), 0);
        }

        Residual net = Residual.of(nRequests, nServers, capacity, eligible);
        int source = 0;
        int sink = nRequests + nServers + 1;
        int[] parent = new int[net.nodes];
        while (net.augmentingPath(source, sink, parent)) {
            for (int v = sink; v != source; ) {
                int edge = parent[v];
                net.push(edge);
                v = net.from(edge);
            }
        }

        List<Assignment> pairs = new ArrayList<>();
        for (int i = 0; i < nRequests; i++) {
            int requestNode = 1 + i;
            for (int e = net.edgeStart(requestNode); e < net.edgeEnd(requestNode); e++) {
                int v = net.target(e);
                if (v >= 1 + nRequests && v <= nRequests + nServers && net.residual(e) == 0) {
                    pairs.add(new Assignment(i, v - 1 - nRequests));
                    break;
                }
            }
        }
        return new Matching(pairs, nRequests - pairs.size());
    }

    /**
     * Assign request cells to facilities. Eligibility is a route of at most {@code maxHops};
     * each facility takes at most {@code perFacilityCapacity} requests.
     */
    public static Placement assignToFacilities(MazeGrid grid, List<Point> requests,
                                               List<Point> facilities, int perFacilityCapacity,
                                               int maxHops) {
        if (perFacilityCapacity < 0 || maxHops < 0) {
            throw new IllegalArgumentException("capacity and maxHops must be >= 0");
        }
        int n = requests.size();
        int k = facilities.size();
        boolean[][] eligible = new boolean[n][k];
        for (int j = 0; j < k; j++) {
            int[][] dist = MazeMetrics.distancesFrom(grid, facilities.get(j));
            for (int i = 0; i < n; i++) {
                Point r = requests.get(i);
                int d = dist[r.row()][r.col()];
                eligible[i][j] = d >= 0 && d <= maxHops;
            }
        }
        int[] capacity = new int[k];
        Arrays.fill(capacity, perFacilityCapacity);
        Matching raw = assign(n, k, capacity, eligible);
        List<Assigned> pairs = new ArrayList<>(raw.pairs().size());
        for (Assignment a : raw.pairs()) {
            pairs.add(new Assigned(requests.get(a.request()), facilities.get(a.server())));
        }
        return new Placement(requests, facilities, pairs, raw.unmatchedRequests());
    }

    /**
     * Residual network for the bipartite reduction. Node 0 is the source, then the requests,
     * then the servers, then the sink.
     */
    private static final class Residual {
        private final int[] offsets;
        private final int[] targets;
        private final int[] owner;
        private final int[] twin;
        private final int[] capacity;
        private final int[] queue;
        private final int nodes;

        private Residual(int[] offsets, int[] targets, int[] owner, int[] twin, int[] capacity, int nodes) {
            this.offsets = offsets;
            this.targets = targets;
            this.owner = owner;
            this.twin = twin;
            this.capacity = capacity;
            this.queue = new int[nodes];
            this.nodes = nodes;
        }

        static Residual of(int nRequests, int nServers, int[] serverCapacity, boolean[][] eligible) {
            int source = 0;
            int sink = nRequests + nServers + 1;
            int nodes = sink + 1;

            int[] degree = new int[nodes];
            degree[source] = nRequests;
            degree[sink] = nServers;
            for (int i = 0; i < nRequests; i++) {
                int edges = 1; // reverse to source
                for (int j = 0; j < nServers; j++) {
                    if (eligible[i][j]) {
                        edges++;
                    }
                }
                degree[1 + i] = edges;
            }
            for (int j = 0; j < nServers; j++) {
                int edges = 1; // forward to sink
                for (int i = 0; i < nRequests; i++) {
                    if (eligible[i][j]) {
                        edges++;
                    }
                }
                degree[1 + nRequests + j] = edges;
            }

            int[] offsets = new int[nodes + 1];
            for (int v = 0; v < nodes; v++) {
                offsets[v + 1] = offsets[v] + degree[v];
            }
            int edges = offsets[nodes];
            int[] targets = new int[edges];
            int[] owner = new int[edges];
            int[] capacity = new int[edges];
            int[] twin = new int[edges];
            int[] cursor = offsets.clone();

            for (int i = 0; i < nRequests; i++) {
                addPair(cursor, targets, owner, capacity, twin, source, 1 + i, 1);
            }
            for (int i = 0; i < nRequests; i++) {
                for (int j = 0; j < nServers; j++) {
                    if (eligible[i][j]) {
                        addPair(cursor, targets, owner, capacity, twin, 1 + i, 1 + nRequests + j, 1);
                    }
                }
            }
            for (int j = 0; j < nServers; j++) {
                addPair(cursor, targets, owner, capacity, twin,
                        1 + nRequests + j, sink, serverCapacity[j]);
            }
            return new Residual(offsets, targets, owner, twin, capacity, nodes);
        }

        private static void addPair(int[] cursor, int[] targets, int[] owner, int[] capacity,
                                    int[] twin, int from, int to, int cap) {
            int e = cursor[from]++;
            int f = cursor[to]++;
            targets[e] = to;
            owner[e] = from;
            capacity[e] = cap;
            twin[e] = f;
            targets[f] = from;
            owner[f] = to;
            capacity[f] = 0;
            twin[f] = e;
        }

        int edgeStart(int node) {
            return offsets[node];
        }

        int edgeEnd(int node) {
            return offsets[node + 1];
        }

        int target(int edge) {
            return targets[edge];
        }

        int from(int edge) {
            return owner[edge];
        }

        int residual(int edge) {
            return capacity[edge];
        }

        void push(int edge) {
            capacity[edge]--;
            capacity[twin[edge]]++;
        }

        boolean augmentingPath(int source, int sink, int[] parentEdge) {
            Arrays.fill(parentEdge, -1);
            boolean[] seen = new boolean[nodes];
            seen[source] = true;
            int head = 0;
            int tail = 0;
            queue[tail++] = source;
            while (head < tail) {
                int u = queue[head++];
                for (int e = offsets[u]; e < offsets[u + 1]; e++) {
                    int v = targets[e];
                    if (!seen[v] && capacity[e] > 0) {
                        seen[v] = true;
                        parentEdge[v] = e;
                        if (v == sink) {
                            return true;
                        }
                        queue[tail++] = v;
                    }
                }
            }
            return false;
        }
    }
}
