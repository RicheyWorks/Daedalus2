// SPDX-License-Identifier: MIT

package com.daedalus.world.gallery;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.ParcelBounds;
import com.daedalus.world.World;
import com.daedalus.world.WorldId;
import com.daedalus.world.gate.GateOps;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Gallery City (ADR-035): parcels of three shapes around the Origin, with addresses on named streets and
 * height limits that fall away from downtown; galleries whose every frame really hangs on a wall with
 * open air in front of it; the drone pad on gate 0's line; and the gates still fit.
 */
class GalleryOpsTest {

    @Test
    void parcelsTileTheBlocksWithAddressesAndHeights() {
        List<GalleryOps.Parcel> parcels = GalleryOps.parcels();
        assertThat(GalleryOps.SIDE).isEqualTo(156);
        assertThat(parcels.size()).isEqualTo(GalleryOps.parcelCount()).isBetween(48, 96);
        Set<BlockCoordinate> footprint = new HashSet<>();
        Set<String> addresses = new HashSet<>();
        int downtown = 0;
        int area = 0;
        for (GalleryOps.Parcel p : parcels) {
            ParcelBounds b = p.bounds();
            assertThat(b.overlaps(GalleryOps.plaza())).isFalse();
            assertThat(b.maxY()).isIn(GalleryOps.HEIGHT_DOWNTOWN, GalleryOps.HEIGHT_OUTSKIRTS);
            if (b.maxY() == GalleryOps.HEIGHT_DOWNTOWN) {
                downtown++;
            }
            assertThat(addresses.add(p.address())).isTrue();
            assertThat(p.address()).matches("\\d+ .+");
            for (int x = b.minX(); x <= b.maxX(); x++) {
                for (int z = b.minZ(); z <= b.maxZ(); z++) {
                    assertThat(footprint.add(new BlockCoordinate(x, 0, z))).isTrue();
                    assertThat(GalleryOps.parcelAt(x, z)).isEqualTo(p.n());
                }
            }
            area += (b.maxX() - b.minX() + 1) * (b.maxZ() - b.minZ() + 1);
            assertThat(GalleryOps.parcelBounds(p.n())).isEqualTo(b);
        }
        assertThat(area).as("every block but the plaza, whole").isEqualTo(24 * GalleryOps.BLOCK * GalleryOps.BLOCK);
        assertThat(downtown).isPositive().isLessThan(parcels.size());
        assertThat(GalleryOps.parcelBounds(-1)).isNull();
        assertThat(GalleryOps.parcelBounds(parcels.size())).isNull();
        assertThat(GalleryOps.streets()).hasSize(12);
    }

    @Test
    void theOriginIsOnGateZerosLine() {
        BlockCoordinate pad = GalleryOps.padBerth();
        assertThat(pad.x()).isEqualTo(GateOps.center(0).x());
        GalleryOps.Plan plan = GalleryOps.plan(1);
        assertThat(plan.cubes().get(new BlockCoordinate(pad.x() - 3, 0, pad.z()))).isEqualTo(BlockType.HELIPAD);
        assertThat(plan.cubes().get(new BlockCoordinate(pad.x() + 7, 10, pad.z() - 7))).isEqualTo(BlockType.CRYSTAL);
        assertThat(GalleryOps.parcelAt(pad.x(), pad.z())).isEqualTo(-1);
    }

    @Test
    void everyGalleryFrameHangsOnARealWallInsideItsParcel() {
        int galleries = 0;
        int parcels = 0;
        for (long seed = 0; seed < 12; seed++) {
            GalleryOps.Plan plan = GalleryOps.plan(seed);
            World w = new World(new WorldId("gallery"));
            assertThat(GalleryOps.build(w, plan)).isTrue();
            for (GalleryOps.Frame f : plan.frames()) {
                assertThat(GalleryOps.fits(w, f)).as("seed %d %s", seed, f).isTrue();
                int n = GalleryOps.parcelAt(f.x(), f.z());
                assertThat(n).isNotNegative();
                ParcelBounds b = GalleryOps.parcelBounds(n);
                for (BlockCoordinate c : f.wall()) {
                    assertThat(b.contains(c)).isTrue();
                }
            }
            for (GalleryOps.Parcel p : plan.parcels()) {
                parcels++;
                if (p.gallery()) {
                    galleries++;
                }
            }
            for (BlockCoordinate c : plan.cubes().keySet()) {
                if (c.y() > 0) {
                    int n = GalleryOps.parcelAt(c.x(), c.z());
                    if (n >= 0) {
                        assertThat(c.y()).isLessThanOrEqualTo(GalleryOps.parcelBounds(n).maxY());
                    }
                }
            }
            if (seed == 0) {
                for (int g = 0; g < GateOps.MAX_GATES; g++) {
                    assertThat(GateOps.fits(w, g)).isTrue();
                }
            }
        }
        assertThat(galleries).as("about two in five open as galleries").isBetween(parcels * 30 / 100, parcels * 50 / 100);
    }

    @Test
    void aFrameNeedsAWallBehindItAndAirInFront() {
        World w = new World(new WorldId("frames"));
        for (int x = 0; x < 4; x++) {
            for (int y = 1; y < 4; y++) {
                w.place(new BlockCoordinate(x, y, 0), BlockType.BRICK_WHITE);
            }
        }
        GalleryOps.Frame ok = new GalleryOps.Frame(0, 1, 0, GalleryOps.Facing.SOUTH, 3, 2, 5);
        assertThat(GalleryOps.fits(w, ok)).isTrue();
        assertThat(GalleryOps.fits(w, new GalleryOps.Frame(2, 1, 0, GalleryOps.Facing.SOUTH, 3, 2, 5))).as("runs off the wall").isFalse();
        assertThat(GalleryOps.fits(w, new GalleryOps.Frame(0, 1, 0, GalleryOps.Facing.SOUTH, 7, 1, 5))).as("too wide").isFalse();
        w.place(new BlockCoordinate(1, 1, 1), BlockType.WOOD);
        assertThat(GalleryOps.fits(w, ok)).as("something in front").isFalse();
        w.place(new BlockCoordinate(1, 1, 1), BlockType.GLASS);
        assertThat(GalleryOps.fits(w, ok)).as("glass in front is fine").isTrue();
        assertThat(ok.overlaps(new GalleryOps.Frame(2, 2, 0, GalleryOps.Facing.SOUTH, 1, 1, 9))).isTrue();
        assertThat(ok.overlaps(new GalleryOps.Frame(3, 1, 0, GalleryOps.Facing.SOUTH, 1, 1, 9))).isFalse();
        assertThat(ok.overlaps(new GalleryOps.Frame(0, 1, 0, GalleryOps.Facing.NORTH, 1, 1, 9))).as("the other face").isFalse();
    }
}
