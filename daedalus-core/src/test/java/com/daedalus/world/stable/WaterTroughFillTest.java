// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.stable.WaterTroughFill.Pipes;
import com.daedalus.world.stable.WaterTroughFill.Plan;

import org.junit.jupiter.api.Test;

class WaterTroughFillTest {

    @Test
    void bestMatchesBruteForceOverEveryFlow() {
        for (long seed = 1; seed <= 300; seed++) {
            Pipes net = WaterTroughFill.pipes(seed, 4, 2);
            int demand = (int) (seed % 4);
            Plan b = WaterTroughFill.best(net, demand);
            assertThat(b.cost()).as("seed %d", seed).isEqualTo(brute(net, demand));
            if (b.cost() != WaterTroughFill.INFEASIBLE) {
                assertThat(WaterTroughFill.pump(net, demand, b.flow())).isEqualTo(b.cost());
                assertThat(WaterTroughFill.quest(net, demand, b.flow())).isTrue();
            }
        }
    }

    @Test
    void cheapestPathIsNeverBetterAndSometimesWorse() {
        int worse = 0;
        for (long seed = 1; seed <= 300; seed++) {
            Pipes net = WaterTroughFill.pipes(seed, 6, 3);
            Plan b = WaterTroughFill.best(net, 4);
            Plan g = WaterTroughFill.cheapestPath(net, 4);
            if (b.cost() == WaterTroughFill.INFEASIBLE) {
                assertThat(g.cost()).isEqualTo(WaterTroughFill.INFEASIBLE);
                continue;
            }
            if (g.cost() == WaterTroughFill.INFEASIBLE) {
                worse++;
                continue;
            }
            assertThat(WaterTroughFill.pump(net, 4, g.flow())).isEqualTo(g.cost());
            assertThat(g.cost()).isGreaterThanOrEqualTo(b.cost());
            if (g.cost() > b.cost()) {
                worse++;
            }
        }
        assertThat(worse).isPositive();
    }

    @Test
    void cheapCrossPipeRunsTheHabitDryOrDear() {
        // Well 0, junctions 1 and 2, trough 3. The cheap zig-zag 0-1-2-3 (cost 3) takes the first bucket and
        // blocks both cross pipes; without pushing water back the second bucket has no room. Best sends
        // 0-1-3 and 0-2-3 for 6 + 6.
        Pipes net = new Pipes(4, new int[] {0, 0, 1, 1, 2}, new int[] {1, 2, 2, 3, 3}, new int[] {1, 1, 1, 1, 1},
                new int[] {1, 5, 1, 5, 1});
        assertThat(WaterTroughFill.cheapestPath(net, 2).cost()).isEqualTo(WaterTroughFill.INFEASIBLE);
        assertThat(WaterTroughFill.best(net, 2)).isEqualTo(new Plan(12, new int[] {1, 1, 0, 1, 1}));
        // With a dear direct pipe the habit does fill the trough, but pays 3 + 20 instead of 12.
        Pipes dear = new Pipes(4, new int[] {0, 0, 1, 1, 2, 0}, new int[] {1, 2, 2, 3, 3, 3},
                new int[] {1, 1, 1, 1, 1, 1}, new int[] {1, 5, 1, 5, 1, 20});
        Plan g = WaterTroughFill.cheapestPath(dear, 2);
        assertThat(g.cost()).isEqualTo(23);
        assertThat(WaterTroughFill.best(dear, 2).cost()).isEqualTo(12);
        assertThat(WaterTroughFill.quest(dear, 2, g.flow())).isFalse();
    }

    @Test
    void leakyOrOverfullPlansAreInfeasible() {
        Pipes net = new Pipes(3, new int[] {0, 1}, new int[] {1, 2}, new int[] {2, 2}, new int[] {1, 1});
        assertThat(WaterTroughFill.pump(net, 2, new int[] {2, 2})).isEqualTo(4);
        assertThat(WaterTroughFill.pump(net, 2, new int[] {2, 1})).isEqualTo(WaterTroughFill.INFEASIBLE);
        assertThat(WaterTroughFill.pump(net, 3, new int[] {3, 3})).isEqualTo(WaterTroughFill.INFEASIBLE);
        assertThat(WaterTroughFill.pump(net, 1, new int[] {2, 2})).isEqualTo(WaterTroughFill.INFEASIBLE);
        assertThat(WaterTroughFill.pump(net, 0, new int[] {-1, -1})).isEqualTo(WaterTroughFill.INFEASIBLE);
        assertThat(WaterTroughFill.pump(net, 2, new int[] {2})).isEqualTo(WaterTroughFill.INFEASIBLE);
        assertThat(WaterTroughFill.best(net, 3).cost()).isEqualTo(WaterTroughFill.INFEASIBLE);
        assertThat(WaterTroughFill.best(net, 0).cost()).isZero();
    }

    @Test
    void deterministicSeedsAndInputChecks() {
        assertThat(WaterTroughFill.pipes(9, 5, 3)).isEqualTo(WaterTroughFill.pipes(9, 5, 3));
        assertThat(WaterTroughFill.QUEST_ID).isEqualTo("q_troughs_full");
        assertThatThrownBy(() -> WaterTroughFill.pipes(1, 1, 3)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Pipes(2, new int[] {0}, new int[] {0}, new int[] {1}, new int[] {1}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Pipes(2, new int[] {0}, new int[] {1}, new int[] {1}, new int[] {-1}))
                .isInstanceOf(IllegalArgumentException.class);
        Pipes net = WaterTroughFill.pipes(2, 3, 2);
        assertThatThrownBy(() -> WaterTroughFill.best(net, -1)).isInstanceOf(IllegalArgumentException.class);
    }

    private static int brute(Pipes net, int demand) {
        return search(net, demand, new int[net.pipes()], 0);
    }

    private static int search(Pipes net, int demand, int[] flow, int i) {
        if (i == flow.length) {
            return WaterTroughFill.pump(net, demand, flow);
        }
        int best = WaterTroughFill.INFEASIBLE;
        int[] cap = net.cap();
        for (int f = 0; f <= cap[i]; f++) {
            flow[i] = f;
            int c = search(net, demand, flow, i + 1);
            if (c != WaterTroughFill.INFEASIBLE && (best == WaterTroughFill.INFEASIBLE || c < best)) {
                best = c;
            }
        }
        flow[i] = 0;
        return best;
    }
}
