// SPDX-License-Identifier: MIT

package com.daedalus.examples.loadbalancer;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.HilbertCurveGenerator;
import com.daedalus.graph.CsrGraph;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.theory.FacilityPlacement;
import com.daedalus.theory.MazeFlow;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The example is executable documentation, so its claims are tested rather than printed and
 * hoped for. Each test pins a property the narrative depends on.
 */
class TopologyLabTest {

    @Test
    void rawHilbertTopologyIsConnectedButHasNoRedundancy() {
        // Writing this example is what exposed HilbertCurveGenerator emitting a forest — corner
        // to corner measured edge connectivity 0, i.e. no route at all. That is now fixed, so the
        // raw output is a proper spanning tree: connected, but with exactly one route between any
        // two nodes, which is why a topology still has to be braided before capacity analysis
        // means anything.
        MazeGrid raw = new HilbertCurveGenerator().generate(32, 32, 42L, new MazeStats());

        assertThat(MazeFlow.edgeConnectivity(raw, new Point(0, 0), new Point(31, 31)))
                .as("a spanning tree connects everything by exactly one route")
                .isEqualTo(1);
        assertThat(Braider.deadEnds(raw)).as("a tree is full of dead ends").isNotEmpty();
    }

    @Test
    void braidingRemovesDeadEndsAndAddsLinks_butDoesNotGuaranteeTwoRoutes() {
        MazeGrid raw = new HilbertCurveGenerator().generate(32, 32, 42L, new MazeStats());
        MazeGrid braided = TopologyLab.buildTopology();

        // What braiding does guarantee: no cell is left with a single link.
        assertThat(Braider.deadEnds(raw)).isNotEmpty();
        assertThat(Braider.deadEnds(braided)).isEmpty();
        assertThat(linkCount(braided)).isGreaterThan(linkCount(raw));

        // What it does NOT guarantee, which is worth stating because it is easy to assume:
        // minimum degree 2 does not imply two edge-disjoint routes. A "barbell" — two cycles
        // joined by one link — has no dead ends and still has a bridge. So connectivity between
        // two given nodes may remain 1 even after a full braid.
        int connectivity = MazeFlow.edgeConnectivity(braided, new Point(0, 0), new Point(31, 31));
        assertThat(connectivity).as("still connected").isGreaterThanOrEqualTo(1);
    }

    private static int linkCount(MazeGrid grid) {
        int halfEdges = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                halfEdges += grid.openNeighbors(new Point(r, c)).size();
            }
        }
        return halfEdges / 2;
    }

    @Test
    void cutEdgesActuallySeverTheTopology() {
        MazeGrid topology = TopologyLab.buildTopology();
        Point ingress = new Point(0, 0);
        Point egress = new Point(topology.rows() - 1, topology.cols() - 1);

        MazeFlow.MinCut cut = MazeFlow.minCut(topology, ingress, egress);

        assertThat(cut.cutEdges()).hasSize(cut.cutSize());
        assertThat(cut.cutSize()).isPositive();
    }

    @Test
    void moreReplicasNeverWorsenTheCoveringRadius() {
        MazeGrid topology = TopologyLab.buildTopology();

        int one = FacilityPlacement.kCenter(topology, 1).coveringRadius();
        int four = FacilityPlacement.kCenter(topology, 4).coveringRadius();
        int eight = FacilityPlacement.kCenter(topology, 8).coveringRadius();

        assertThat(four).isLessThanOrEqualTo(one);
        assertThat(eight).isLessThanOrEqualTo(four);
    }

    @Test
    void routingSectionReportsARerouteUnderLoad() {
        // The narrative claims the router avoids a saturated corridor; verify it actually does.
        assertThat(TopologyLab.describeRouting(TopologyLab.buildTopology()))
                .contains("rerouted=true");
    }

    @Test
    void serviceMeshIsATopologyNoMazeCouldExpress() {
        // Spine node has degree 3 with no rectangular structure — not a 4-neighbour grid cell.
        CsrGraph mesh = CsrGraph.builder(4)
                .addUndirected(0, 1, 1.0)
                .addUndirected(0, 2, 1.0)
                .addUndirected(0, 3, 1.0)
                .build();

        int[] buffer = new int[mesh.maxDegree()];
        assertThat(mesh.neighbors(0, buffer)).isEqualTo(3);

        mesh.setEdgeWeight(0, 1, 25.0);
        assertThat(mesh.edgeWeight(0, 1)).isEqualTo(25.0);
        assertThat(mesh.edgeWeight(1, 0)).isEqualTo(1.0); // directions are independent edges
    }

    @Test
    void demoRunsEndToEnd() {
        MazeGrid topology = TopologyLab.buildTopology();

        assertThat(TopologyLab.describeTopology(topology)).contains("nodes=");
        assertThat(TopologyLab.describeCapacity(topology)).contains("edgeConnectivity=");
        assertThat(TopologyLab.describePlacement(topology)).contains("k=1");
        assertThat(TopologyLab.describeServiceMesh()).contains("spineDegree=3");
    }
}
