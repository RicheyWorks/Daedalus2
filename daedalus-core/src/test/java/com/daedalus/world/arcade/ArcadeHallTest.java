// SPDX-License-Identifier: MIT

package com.daedalus.world.arcade;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.PortalResult;
import com.daedalus.world.PortalState;
import com.daedalus.world.WorldId;
import java.io.BufferedReader;
import java.io.StringReader;
import org.junit.jupiter.api.Test;

class ArcadeHallTest {

    @Test
    void assemblerLayoutsLoad() {
        assertThat(ArcadeHall.layouts()).extracting(ArcadeHall.Layout::id).contains("corner_arcade", "prize_hall", "heart_hall");
        for (ArcadeHall.Layout l : ArcadeHall.layouts()) {
            assertThat(l.cabs()).as(l.id()).isPositive();
            assertThat(l.spawnInsideY()).as(l.id()).isPositive().isLessThan(l.depthM());
            assertThat(l.spawnInsideX()).as(l.id()).isEqualTo(l.doorX());
        }
    }

    @Test
    void playerWalksFromIslandIntoHall() {
        BlockCoordinate anchor = new BlockCoordinate(40, 12, -8);
        ArcadeHall hall = ArcadeHall.onIsland("prize_hall", WorldId.ZERO, anchor);
        assertThat(hall.door().at()).isEqualTo(anchor);
        assertThat(hall.door().state()).isEqualTo(PortalState.SEALED);
        assertThat(hall.inside(anchor)).isFalse();

        ArcadeHall.Entry first = hall.enter();
        assertThat(first.entered()).isTrue();
        assertThat(first.firstVisit()).isTrue();
        assertThat(first.portal()).isEqualTo(PortalResult.OPENED);
        assertThat(hall.inside(first.spawn())).isTrue();
        assertThat(first.spawn().y()).isEqualTo(anchor.y());

        ArcadeHall.Entry again = hall.enter();
        assertThat(again.firstVisit()).isFalse();
        assertThat(again.portal()).isEqualTo(PortalResult.ALREADY_OPEN);
        assertThat(hall.describe()).startsWith(ArcadeHall.HALL_NAME);
    }

    @Test
    void entranceStepsAndPathLeadOutOntoTheIsland() {
        BlockCoordinate anchor = new BlockCoordinate(10, 20, 30);
        ArcadeHall hall = ArcadeHall.onIsland("heart_hall", WorldId.ZERO, anchor);
        BlockCoordinate foot = hall.stepsFoot();
        BlockCoordinate start = hall.pathStart();
        assertThat(hall.inside(foot)).isFalse();
        assertThat(hall.inside(start)).isFalse();
        assertThat(foot.x()).isEqualTo(anchor.x());
        assertThat(foot.z()).isLessThan(anchor.z());
        assertThat(start.z()).isLessThan(foot.z());
        assertThat(anchor.z() - start.z()).isEqualTo((int) Math.ceil(ArcadeHall.STEPS_RUN_M + ArcadeHall.PATH_TILES * ArcadeHall.PATH_TILE_M));
        assertThat(ArcadeHall.FOUNDATION_M).isLessThan(1.0);
    }

    @Test
    void unknownLayoutAndBadRowsRejected() {
        assertThatThrownBy(() -> ArcadeHall.onIsland("nope", WorldId.ZERO, new BlockCoordinate(0, 0, 0))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ArcadeHall.parse(new BufferedReader(new StringReader("x\ty\t1\t1\t0\t1\t1\t1\t1\n"))))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ArcadeHall.parse(new BufferedReader(new StringReader("x\ty\t4\t3\t9\t1\t1\t1\t1\n"))))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
