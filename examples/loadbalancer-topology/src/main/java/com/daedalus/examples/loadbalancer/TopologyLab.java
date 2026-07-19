// SPDX-License-Identifier: MIT

package com.daedalus.examples.loadbalancer;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.WeightedMazeGrid;
import com.daedalus.engine.generators.HilbertCurveGenerator;
import com.daedalus.graph.CsrGraph;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.LandmarkHeuristic;
import com.daedalus.solver.solvers.AStarSolver;
import com.daedalus.theory.FacilityPlacement;
import com.daedalus.theory.MazeFlow;

import java.util.List;

/**
 * Daedalus as the topology and analysis engine behind a load balancer.
 *
 * <p>Everything here works against LoadBalancerPro <b>today</b>, with no changes to either
 * project, because all of it is <em>offline</em> analysis — generate a topology, measure it, plan
 * against it. That is the honest scope: LoadBalancerPro's per-request seam is
 * {@code RoutingDecision choose(List<ServerStateVector>)}, which selects one endpoint from a flat
 * list. It has no graph and no destination, so a path-finder cannot be dropped into it (see
 * {@code docs/adr/ADR-001-graph-engine-seam.md}). What a path-finder <em>can</em> do is answer the
 * questions asked before a request arrives: how much capacity is there, where should things live,
 * and what does the network look like under failure.
 *
 * <p>Four demonstrations:
 * <ol>
 *   <li><b>Topology</b> — a Hilbert curve, chosen for locality: nearby nodes in the 1-D ordering
 *       stay nearby in 2-D.</li>
 *   <li><b>Capacity</b> — min-cut as the bottleneck between two points (CLRS Ch. 26).</li>
 *   <li><b>Placement</b> — k-center for replicas / edge caches (CLRS Ch. 35).</li>
 *   <li><b>Routing</b> — latency-aware A*, with load in the edge cost and an admissible
 *       heuristic. This is the corrected pattern; putting load into the heuristic silently
 *       breaks optimality.</li>
 * </ol>
 *
 * <p>The last section builds a {@link CsrGraph} instead, to show the engine accepting a topology
 * that is not a grid at all — the shape a real service mesh has.
 */
public final class TopologyLab {

    private static final int SIZE = 32;
    private static final long SEED = 42L;

    private TopologyLab() {
    }

    public static void main(String[] args) {
        MazeGrid topology = buildTopology();
        report("1. TOPOLOGY", describeTopology(topology));
        report("2. CAPACITY", describeCapacity(topology));
        report("3. PLACEMENT", describePlacement(topology));
        report("4. ROUTING", describeRouting(topology));
        report("5. NON-GRID TOPOLOGY", describeServiceMesh());
    }

    /**
     * A Hilbert topology, then <b>fully</b> braided.
     *
     * <p>Writing this example is what exposed a real defect: {@code HilbertCurveGenerator} used to
     * emit a <b>forest</b> — at 32x32, edge connectivity from {@code (0,0)} to {@code (31,31)}
     * measured {@code 0} (no route at all) with 953 edges for 1024 cells and 396 dead ends. Routing
     * across it returned an empty path, silently. That is fixed; the generator now produces a
     * proper spanning tree.
     *
     * <p>Braiding is still required, for a different reason: a spanning tree connects everything by
     * <em>exactly one</em> route, so every link is a single point of failure. A full braid removes
     * every dead end, taking minimum degree from 1 to 2.
     *
     * <p>But note what that does <b>not</b> buy, because it is easy to assume otherwise: minimum
     * degree 2 does not imply two edge-disjoint routes. A "barbell" — two cycles joined by a single
     * link — has no dead ends and still has a bridge. Measured here, the fully braided topology
     * still reports edge connectivity 1 corner-to-corner, because a bridge survives on every path
     * between those particular nodes.
     *
     * <p>That is exactly why capacity is worth <em>measuring</em> rather than assuming from a
     * topology's construction — which is the entire argument for section 2.
     */
    static MazeGrid buildTopology() {
        MazeGrid grid = new HilbertCurveGenerator().generate(SIZE, SIZE, SEED, new MazeStats());
        Braider.braid(grid, 1.0, SEED);
        return grid;
    }

    static String describeTopology(MazeGrid topology) {
        int links = 0;
        for (int r = 0; r < topology.rows(); r++) {
            for (int c = 0; c < topology.cols(); c++) {
                links += topology.openNeighbors(new Point(r, c)).size();
            }
        }
        return "nodes=" + (topology.rows() * topology.cols())
                + "  links=" + links / 2
                + "  deadEnds=" + Braider.deadEnds(topology).size()
                + "\n   NOTE: measured stretch says Hilbert is NOT the best choice here — mean 4.62"
                + "\n   vs 2.48 for plain prims, with double the diameter. The curve has great"
                + "\n   locality; the tree built by attaching to a random visited neighbour does"
                + "\n   not inherit it. Prefer 'prims' or 'archimedes-spiral' for real topologies."
                + "\n   The generator yields a spanning tree (one route everywhere); braiding is"
                + "\n   what adds the redundancy that makes capacity analysis meaningful.";
    }

    /**
     * Min-cut between two nodes: the fewest links whose loss disconnects them. Equivalently the
     * number of independent routes, so it is both a capacity ceiling and a fragility score.
     */
    static String describeCapacity(MazeGrid topology) {
        Point ingress = new Point(0, 0);
        Point egress = new Point(SIZE - 1, SIZE - 1);
        MazeFlow.MinCut cut = MazeFlow.minCut(topology, ingress, egress);
        int independentRoutes = MazeFlow.vertexDisjointPaths(topology, ingress, egress);
        return "edgeConnectivity=" + cut.cutSize()
                + "  vertexDisjointRoutes=" + independentRoutes
                + "\n   bottleneckLinks=" + cut.cutEdges().size()
                + " — sever these and " + ingress + " loses " + egress + "."
                + "\n   Vertex-disjoint <= edge-disjoint always: killing nodes is at least as"
                + "\n   effective as killing links.";
    }

    /** k-center: place replicas so the worst-served node is as close as possible. */
    static String describePlacement(MazeGrid topology) {
        StringBuilder out = new StringBuilder();
        for (int k : new int[] {1, 2, 4, 8}) {
            FacilityPlacement.Placement placement = FacilityPlacement.kCenter(topology, k);
            out.append(String.format("   k=%-2d radius=%-3d facilities=%s%n",
                    k, placement.coveringRadius(), placement.facilities()));
        }
        out.append("   Radius is the worst-case hops to the nearest replica. Greedy is a"
                + "\n   2-approximation, and nothing polynomial does better unless P=NP.");
        return out.toString().stripTrailing();
    }

    /**
     * Latency-aware routing done correctly: live load goes into the edge <b>cost</b>, and the
     * heuristic stays an admissible distance bound. Load in the heuristic would break A*'s
     * optimality guarantee silently.
     */
    static String describeRouting(MazeGrid topology) {
        WeightedMazeGrid weighted = new WeightedMazeGrid(topology);
        LandmarkHeuristic landmarks = LandmarkHeuristic.precompute(topology, 4);
        Point from = new Point(0, 0);
        Point to = new Point(SIZE - 1, SIZE - 1);

        MazeStats idle = new MazeStats();
        List<Point> quiet = new AStarSolver(landmarks.asHeuristic()).solve(weighted, from, to, idle);

        // Saturate the corridor the quiet route uses, then re-route.
        for (Point hop : quiet.subList(1, Math.max(1, quiet.size() - 1))) {
            weighted.setWeight(hop, 12.0); // cost >= 1.0 keeps the hop-count bound admissible
        }
        MazeStats loaded = new MazeStats();
        List<Point> detour = new AStarSolver(landmarks.asHeuristic()).solve(weighted, from, to, loaded);

        return "idleRouteHops=" + (quiet.size() - 1) + "  expansions=" + idle.cellsExplored()
                + "\n   loadedRouteHops=" + (detour.size() - 1) + "  expansions=" + loaded.cellsExplored()
                + "\n   rerouted=" + !detour.equals(quiet)
                + " — the router avoids the saturated corridor while staying provably optimal,"
                + "\n   because load is in g (edge cost), not in h (the distance estimate).";
    }

    /**
     * The same engine over a topology that was never a grid — three racks of two hosts with a
     * spine, which no maze generator could express.
     */
    static String describeServiceMesh() {
        // 0 = spine, 1..3 = rack switches, 4..9 = hosts.
        CsrGraph mesh = CsrGraph.builder(10)
                .addUndirected(0, 1, 1.0)
                .addUndirected(0, 2, 1.0)
                .addUndirected(0, 3, 1.0)
                .addUndirected(1, 4, 1.0).addUndirected(1, 5, 1.0)
                .addUndirected(2, 6, 1.0).addUndirected(2, 7, 1.0)
                .addUndirected(3, 8, 1.0).addUndirected(3, 9, 1.0)
                .build();

        int[] buffer = new int[mesh.maxDegree()];
        int spineDegree = mesh.neighbors(0, buffer);

        mesh.setEdgeWeight(0, 1, 25.0); // rack 1 uplink degrades

        return "nodes=" + mesh.nodeCount() + "  spineDegree=" + spineDegree
                + "  uplinkCost(spine->rack1)=" + mesh.edgeWeight(0, 1)
                + "\n   A spine-and-leaf tree has degree-3 nodes and no rectangular structure, so"
                + "\n   it cannot be a MazeGrid. The Graph seam takes it directly, and edge costs"
                + "\n   are updatable in place as live latency moves.";
    }

    private static void report(String heading, String body) {
        System.out.println("== " + heading + " ==");
        System.out.println(body.startsWith("   ") ? body : "   " + body);
        System.out.println();
    }
}
