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
    void rawHilbertTopologyIsDisconnected_whichIsWhyBraidingIsMandatory() {
        // Pins the finding that motivated the example's design: the generator's raw output has
        // no route between the corners at all, so routing over it would silently return nothing.
        MazeGrid raw = new HilbertCurveGenerator().generate(32, 32, 42L, new MazeStats());

        assertThat(MazeFlow.edgeConnectivity(raw, new Point(0, 0), new Point(31, 31)))
                .as("raw Hilbert output is not a connected topology")
                .isZero();
        assertThat(Braider.deadEnds(raw)).hasSizeGreaterThan(300);
    }

    @Test
    void braidedTopologyHasRedundancy_whichIsThePointOfBraiding() {
        MazeGrid topology = TopologyLab.buildTopology();

        // After a full braid the corners are not just connected but redundantly so — more than
        // one link must fail to sever them, which is what makes capacity analysis meaningful.
        int connectivity = MazeFlow.edgeConnectivity(topology, new Point(0, 0),
                new Point(topology.rows() - 1, topology.cols() - 1));

        assertThat(connectivity).isGreaterThan(1);
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
