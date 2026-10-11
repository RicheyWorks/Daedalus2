// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import com.daedalus.world.BlockCoordinate;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.function.IntFunction;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ArkFleetTest {

    /** Three islands on the lane, 96 apart; slot 3 is empty sky. */
    private static final IntFunction<BlockCoordinate> BERTHS =
            slot -> slot <= 2 ? new BlockCoordinate(slot * 96, 50, -70) : null;

    @Test
    void anArkSailsArrivesAndMoorsAtTheDestination() {
        ArkFleet fleet = new ArkFleet();
        assertThat(fleet.slotOf("ark-0", 0)).isZero();
        ArkFleet.Outcome out = fleet.sail("ark-0", 0, 2, BERTHS, 1_000);
        assertThat(out.result()).isEqualTo(VoyageResult.SAILING);
        Voyage v = out.voyage();
        assertThat(v.fromSlot()).isZero();
        assertThat(v.toSlot()).isEqualTo(2);
        // 192 cubes at 12/s is 16 s, plus 4 s to cast off and tie up.
        assertThat(v.arriveAt() - v.departAt()).isEqualTo(20_000);
        assertThat(fleet.voyageOf("ark-0")).isEqualTo(v);
        assertThat(v.progress(11_000)).isEqualTo(0.5);
        assertThat(fleet.settle(20_999)).isEmpty();
        assertThat(fleet.settle(21_000)).containsExactly(v);
        assertThat(fleet.voyageOf("ark-0")).isNull();
        assertThat(fleet.slotOf("ark-0", 0)).isEqualTo(2);
        // Settling twice does not arrive twice.
        assertThat(fleet.settle(99_000)).isEmpty();
    }

    @Test
    void ordersWhileSailingOrToTheSameIslandOrToEmptySkyAreNamed() {
        ArkFleet fleet = new ArkFleet();
        assertThat(fleet.sail("ark-1", 1, 1, BERTHS, 0).result()).isEqualTo(VoyageResult.ALREADY_THERE);
        assertThat(fleet.sail("ark-1", 1, 3, BERTHS, 0).result()).isEqualTo(VoyageResult.NO_SUCH_ISLAND);
        Voyage first = fleet.sail("ark-1", 1, 0, BERTHS, 0).voyage();
        ArkFleet.Outcome again = fleet.sail("ark-1", 1, 2, BERTHS, 5_000);
        assertThat(again.result()).isEqualTo(VoyageResult.UNDERWAY);
        assertThat(again.voyage()).isEqualTo(first);
        // After arrival the ark takes the next order from where it is now.
        fleet.settle(first.arriveAt());
        Voyage second = fleet.sail("ark-1", 1, 2, BERTHS, first.arriveAt() + 1).voyage();
        assertThat(second.fromSlot()).isZero();
    }

    @Test
    void theFleetSurvivesARestartMidVoyage() {
        ArkFleet fleet = new ArkFleet();
        fleet.sail("ark-0", 0, 1, BERTHS, 100);
        Voyage v = fleet.sail("ark-2", 2, 0, BERTHS, 200).voyage();
        fleet.settle(fleet.voyageOf("ark-0").arriveAt());
        List<String> lines = fleet.toLines();
        ArkFleet back = ArkFleet.fromLines(lines);
        assertThat(back.toLines()).isEqualTo(lines);
        assertThat(back.slotOf("ark-0", 0)).isEqualTo(1);
        assertThat(back.voyageOf("ark-0")).isNull();
        assertThat(back.voyageOf("ark-2")).isEqualTo(v);
        assertThat(back.settle(v.arriveAt())).containsExactly(v);
    }

    @Test
    void aVoyageMustTakeTimeAndBadRowsAreRefused() {
        assertThatThrownBy(() -> new Voyage("x", 0, 1, 10, 10)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ArkFleet.fromLines(List.of("ark-0 1 2")))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
