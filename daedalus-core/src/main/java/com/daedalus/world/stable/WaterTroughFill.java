// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * G539 Water Trough Fill (Studio horse lane): the stable hand must pump a required number of
 * buckets from the well (node 0) to the trough (last node) through one-way pipes, each with a
 * capacity in buckets and a pumping cost per bucket. {@link #best} delivers the buckets at the least
 * total cost, exactly, by successive shortest paths on the residual network (Bellman-Ford, so water
 * already sent may be pushed back along a pipe when a cheaper plan appears). {@link #cheapestPath}
 * (keep sending water down the cheapest pipe path that still has room, never undoing a pipe) can pay
 * more or run dry before the trough is full. Plain int[] API; the algorithm is small and pure so it
 * can be ported to C++ for Unreal.
 */
public final class WaterTroughFill {

    public static final String QUEST_ID = "q_troughs_full";
    public static final int INFEASIBLE = -1;

    /** Pipe network: node count and per-pipe endpoints, capacity and cost per bucket. */
    public record Pipes(int nodes, int[] from, int[] to, int[] cap, int[] cost) {
        public Pipes {
            from = from.clone();
            to = to.clone();
            cap = cap.clone();
            cost = cost.clone();
            int e = from.length;
            if (nodes < 2 || to.length != e || cap.length != e || cost.length != e) {
                throw new IllegalArgumentException("bad pipes");
            }
            for (int i = 0; i < e; i++) {
                if (from[i] < 0 || from[i] >= nodes || to[i] < 0 || to[i] >= nodes || from[i] == to[i]
                        || cap[i] < 0 || cost[i] < 0) {
                    throw new IllegalArgumentException("bad pipe " + i);
                }
            }
        }

        @Override
        public int[] from() {
            return from.clone();
        }

        @Override
        public int[] to() {
            return to.clone();
        }

        @Override
        public int[] cap() {
            return cap.clone();
        }

        @Override
        public int[] cost() {
            return cost.clone();
        }

        /** Number of pipes. */
        public int pipes() {
            return from.length;
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Pipes p && p.nodes == nodes && Arrays.equals(p.from, from) && Arrays.equals(p.to, to)
                    && Arrays.equals(p.cap, cap) && Arrays.equals(p.cost, cost);
        }

        @Override
        public int hashCode() {
            return Arrays.hashCode(new int[] {nodes, Arrays.hashCode(from), Arrays.hashCode(to),
                Arrays.hashCode(cap), Arrays.hashCode(cost)});
        }

        @Override
        public String toString() {
            return "Pipes[" + nodes + ", from=" + Arrays.toString(from) + ", to=" + Arrays.toString(to)
                    + ", cap=" + Arrays.toString(cap) + ", cost=" + Arrays.toString(cost) + "]";
        }
    }

    /** A pumping plan: total cost (or INFEASIBLE) and buckets per pipe (empty when infeasible). */
    public record Plan(int cost, int[] flow) {
        public Plan {
            flow = flow.clone();
        }

        @Override
        public int[] flow() {
            return flow.clone();
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Plan p && p.cost == cost && Arrays.equals(p.flow, flow);
        }

        @Override
        public int hashCode() {
            return 31 * cost + Arrays.hashCode(flow);
        }

        @Override
        public String toString() {
            return "Plan[" + cost + ", " + Arrays.toString(flow) + "]";
        }
    }

    private WaterTroughFill() { }

    /**
     * Seeded network on {@code nodes} nodes: each downhill pipe i to j (i < j) is laid with
     * probability 3/5 and each uphill one with probability 1/5; capacities in [1, maxCap], costs in [1, 9].
     */
    public static Pipes pipes(long seed, int nodes, int maxCap) {
        if (nodes < 2 || nodes > 12 || maxCap < 1) {
            throw new IllegalArgumentException("bad network request");
        }
        SplittableRandom rnd = new SplittableRandom(seed);
        int max = nodes * (nodes - 1);
        int[] from = new int[max];
        int[] to = new int[max];
        int[] cap = new int[max];
        int[] cost = new int[max];
        int e = 0;
        for (int i = 0; i < nodes; i++) {
            for (int j = 0; j < nodes; j++) {
                if (i != j && rnd.nextInt(5) < (i < j ? 3 : 1)) {
                    from[e] = i;
                    to[e] = j;
                    cap[e] = 1 + rnd.nextInt(maxCap);
                    cost[e] = 1 + rnd.nextInt(9);
                    e++;
                }
            }
        }
        return new Pipes(nodes, Arrays.copyOf(from, e), Arrays.copyOf(to, e), Arrays.copyOf(cap, e),
                Arrays.copyOf(cost, e));
    }

    /** Cheapest way to deliver {@code demand} buckets from the well to the trough (successive shortest paths). */
    public static Plan best(Pipes net, int demand) {
        return route(net, demand, true);
    }

    /** Naive habit: cheapest path with room each time, never pushing water back along a pipe. */
    public static Plan cheapestPath(Pipes net, int demand) {
        return route(net, demand, false);
    }

    private static Plan route(Pipes net, int demand, boolean undo) {
        if (demand < 0) {
            throw new IllegalArgumentException("negative demand");
        }
        int e = net.pipes();
        int n = net.nodes;
        int sink = n - 1;
        int[] flow = new int[e];
        int sent = 0;
        int total = 0;
        while (sent < demand) {
            int[] dist = new int[n];
            int[] via = new int[n];
            Arrays.fill(dist, Integer.MAX_VALUE);
            Arrays.fill(via, -1);
            dist[0] = 0;
            for (int round = 0; round < n; round++) {
                boolean moved = false;
                for (int i = 0; i < e; i++) {
                    int a = net.from[i];
                    int b = net.to[i];
                    if (dist[a] != Integer.MAX_VALUE && flow[i] < net.cap[i] && dist[a] + net.cost[i] < dist[b]) {
                        dist[b] = dist[a] + net.cost[i];
                        via[b] = 2 * i;
                        moved = true;
                    }
                    if (undo && dist[b] != Integer.MAX_VALUE && flow[i] > 0 && dist[b] - net.cost[i] < dist[a]) {
                        dist[a] = dist[b] - net.cost[i];
                        via[a] = 2 * i + 1;
                        moved = true;
                    }
                }
                if (!moved) {
                    break;
                }
            }
            if (dist[sink] == Integer.MAX_VALUE) {
                return new Plan(INFEASIBLE, new int[0]);
            }
            int push = demand - sent;
            for (int v = sink; v != 0;) {
                int i = via[v] / 2;
                if (via[v] % 2 == 0) {
                    push = Math.min(push, net.cap[i] - flow[i]);
                    v = net.from[i];
                } else {
                    push = Math.min(push, flow[i]);
                    v = net.to[i];
                }
            }
            for (int v = sink; v != 0;) {
                int i = via[v] / 2;
                if (via[v] % 2 == 0) {
                    flow[i] += push;
                    v = net.from[i];
                } else {
                    flow[i] -= push;
                    v = net.to[i];
                }
            }
            sent += push;
            total += push * dist[sink];
        }
        return new Plan(total, flow);
    }

    /** Cost of a plan, or INFEASIBLE when a pipe overflows, water leaks at a junction or the trough is short. */
    public static int pump(Pipes net, int demand, int[] flow) {
        int e = net.pipes();
        if (flow.length != e) {
            return INFEASIBLE;
        }
        int[] balance = new int[net.nodes];
        int total = 0;
        for (int i = 0; i < e; i++) {
            if (flow[i] < 0 || flow[i] > net.cap[i]) {
                return INFEASIBLE;
            }
            balance[net.from[i]] -= flow[i];
            balance[net.to[i]] += flow[i];
            total += flow[i] * net.cost[i];
        }
        for (int v = 1; v < net.nodes - 1; v++) {
            if (balance[v] != 0) {
                return INFEASIBLE;
            }
        }
        if (balance[0] != -demand || balance[net.nodes - 1] != demand) {
            return INFEASIBLE;
        }
        return total;
    }

    /** Quest q_troughs_full: the plan fills the trough legally at the least pumping cost. */
    public static boolean quest(Pipes net, int demand, int[] flow) {
        int got = pump(net, demand, flow);
        return got != INFEASIBLE && got == best(net, demand).cost();
    }
}
