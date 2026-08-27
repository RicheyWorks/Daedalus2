// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.api.dto.Hotspot;
import com.daedalus.model.Point;
import com.daedalus.model.TileType;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

/**
 * Canvas geometry without a JavaFX toolkit. {@code MainController#redraw}
 * used to be the only copy of these rules, and nothing tested them.
 */
class DesktopPaintTest {

    @Test
    void aSquareCanvasUsesThinWallsAndAWideCanvasLetterboxes() {
        DesktopPaint.Layout square = DesktopPaint.Layout.fit(5, 5, 100, 100);
        assertThat(square)
                .as("a 5×5 tile grid (2×2 cells) should fit the canvas")
                .isNotNull();
        assertThat(square.cellSize())
                .as("passage size wins: 100 / (2·1.25 + 0.25) floors to 36")
                .isEqualTo(36.0);
        assertThat(square.wall())
                .as("walls are a quarter of the passage, not the same square")
                .isEqualTo(9.0);
        assertThat(square.w(0)).isEqualTo(9.0);
        assertThat(square.w(1)).isEqualTo(36.0);
        assertThat(square.offX()[5]).isEqualTo(99.0);
        assertThat(square.offsetX()).isZero();
        assertThat(square.offsetY()).isZero();

        DesktopPaint.Layout wide = DesktopPaint.Layout.fit(5, 5, 200, 100);
        assertThat(wide.cellSize())
                .as("the short axis owns cell size so the maze is not stretched")
                .isEqualTo(36.0);
        assertThat(wide.offsetX())
                .as("leftover width is split as letterbox, not left-aligned")
                .isEqualTo(50.0);
        assertThat(wide.offsetY()).isZero();
    }

    @Test
    void anEmptyCanvasOrEmptyGridIsNothingToPaint() {
        assertThat(DesktopPaint.Layout.fit(5, 5, 0, 100)).isNull();
        assertThat(DesktopPaint.Layout.fit(0, 5, 100, 100)).isNull();
    }

    @Test
    void thePathSkipsEndpointsAndPaintsTheOpeningBetweenCells() {
        Point start = new Point(0, 0);
        Point mid = new Point(0, 1);
        Point goal = new Point(0, 2);
        List<DesktopPaint.TileRect> tiles = DesktopPaint.pathOverlay(
                List.of(start, mid, goal), start, goal);

        assertThat(tiles)
                .as("start and goal stay their own colors; mid and both connectors paint")
                .containsExactly(
                        new DesktopPaint.TileRect(1, 3),
                        new DesktopPaint.TileRect(1, 2),
                        new DesktopPaint.TileRect(1, 4));
    }

    @Test
    void aNonAdjacentStepDoesNotPaintAChordThroughAWall() {
        Point a = new Point(0, 0);
        Point b = new Point(2, 2);
        assertThat(DesktopPaint.pathOverlay(List.of(a, b), a, b))
                .as("a teleport pair is two endpoints — no connector tile")
                .isEmpty();
    }

    @Test
    void aSolvePathUnfoldsInsteadOfAppearingFinished() {
        List<Point> path = List.of(
                new Point(0, 0), new Point(0, 1), new Point(0, 2), new Point(0, 3));
        assertThat(DesktopPaint.pathPrefix(path, 0)).isEmpty();
        assertThat(DesktopPaint.pathPrefix(path, 0.5)).containsExactly(
                new Point(0, 0), new Point(0, 1));
        assertThat(DesktopPaint.pathPrefix(path, 1)).hasSize(4);
        assertThat(DesktopPaint.pathRevealMs(10)).isEqualTo(700);
        assertThat(DesktopPaint.pathRevealMs(300)).isEqualTo(4200);
        assertThat(DesktopPaint.pathRevealMs(800)).isEqualTo(5000);
        assertThat(DesktopPaint.pathPrefix(null, 0.5)).isEmpty();
        assertThat(DesktopPaint.walkHead(DesktopPaint.pathPrefix(path, 0.5)))
                .isEqualTo(new Point(0, 1));
        assertThat(DesktopPaint.walkHead(List.of())).isNull();
        assertThat(DesktopPaint.PATH_ALPHA).isEqualTo(0.85);
        DesktopPaint.Layout layout = DesktopPaint.Layout.fit(3, 3, 30, 30);
        DesktopPaint.Marker head = DesktopPaint.pathHeadMarker(layout, List.of(new Point(0, 0)));
        DesktopPaint.Marker player = DesktopPaint.playerMarker(layout, new Point(0, 0));
        assertThat(head).isNotNull();
        assertThat(head.size())
                .as("web head radius is 0.38·cell")
                .isCloseTo(15.2, within(1e-9));
        assertThat(head.size()).isLessThan(player.size());
    }

    @Test
    void aMazeFitsAboveTheOverlayLegend() {
        DesktopPaint.Layout full = DesktopPaint.Layout.fit(5, 5, 100, 100);
        DesktopPaint.Layout maze = DesktopPaint.Layout.fitMaze(5, 5, 100, 100);
        assertThat(DesktopPaint.LEGEND_RESERVE).isEqualTo(40);
        assertThat(DesktopPaint.EXPORT_RESERVE).isEqualTo(28);
        assertThat(full).isNotNull();
        assertThat(maze).isNotNull();
        assertThat(maze.cellSize())
                .as("the key and PNG keep their bands so passages are not under chrome")
                .isLessThan(full.cellSize());
        assertThat(maze.offsetY())
                .as("the first row stays below the PNG")
                .isGreaterThanOrEqualTo(DesktopPaint.EXPORT_RESERVE);
        assertThat(maze.offsetY() + maze.offY()[maze.tileRows()])
                .as("the painted maze stays in the band above the legend")
                .isLessThanOrEqualTo(100 - DesktopPaint.LEGEND_RESERVE);
    }

    @Test
    void theLegendNamesOnlyWhatIsOnTheBoard() {
        assertThat(DesktopPaint.legendKeys(false, true, true)).isEmpty();
        assertThat(DesktopPaint.legendKeys(true, false, false))
                .containsExactly("floor", "wall", "start", "goal");
        assertThat(DesktopPaint.legendKeys(true, true, true))
                .containsExactly("floor", "wall", "start", "goal", "path", "player");
        assertThat(DesktopPaint.legendKeys(true, false, false, true))
                .containsExactly("floor", "wall", "start", "goal", "hotspot");
        DesktopPaint.Fog fog = DesktopPaint.Fog.of(
                List.of(new Point(0, 0)), new Point(0, 0), null);
        assertThat(DesktopPaint.legendKeys(true, true, true, true, fog))
                .as("fog swallows the solver path and hot spots; the goal stays hidden")
                .containsExactly("floor", "wall", "start", "player", "fog");
        DesktopPaint.Fog arrived = DesktopPaint.Fog.of(
                List.of(new Point(0, 0)), new Point(0, 0), new Point(2, 2));
        assertThat(DesktopPaint.legendKeys(true, false, true, false, arrived))
                .containsExactly("floor", "wall", "start", "goal", "player", "fog");
    }

    @Test
    void fogRevealsStoodOnCellsAndTheWallsThatTouchThem() {
        DesktopPaint.Fog fog = DesktopPaint.Fog.of(
                List.of(new Point(0, 0)), new Point(0, 0), null);
        assertThat(DesktopPaint.fogRevealsTile(fog, 1, 1))
                .as("the cell underfoot is memory")
                .isTrue();
        assertThat(DesktopPaint.fogRevealsTile(fog, 1, 0))
                .as("the west wall touches the stood-on cell")
                .isTrue();
        assertThat(DesktopPaint.fogRevealsTile(fog, 0, 1))
                .as("the north wall touches the stood-on cell")
                .isTrue();
        assertThat(DesktopPaint.fogRevealsTile(fog, 5, 5))
                .as("a far cell stays unseen void")
                .isFalse();
        assertThat(DesktopPaint.fogRevealsTile(null, 5, 5)).isTrue();
        assertThat(DesktopPaint.fogLamp(fog, 1, 1))
                .as("underfoot is the bright end of the lamp")
                .isEqualTo(1.0);
        assertThat(DesktopPaint.fogLamp(fog, 1, 5))
                .as("two cells east: max(0.38, 1 - 0.24)")
                .isCloseTo(0.76, within(1e-9));
        assertThat(DesktopPaint.mixHex(DesktopPaint.FOG_FLOOR_DIM,
                DesktopPaint.FOG_FLOOR, 0)).isEqualTo(DesktopPaint.FOG_FLOOR_DIM);
        assertThat(DesktopPaint.mixHex(DesktopPaint.FOG_FLOOR_DIM,
                DesktopPaint.FOG_FLOOR, 1)).isEqualTo(DesktopPaint.FOG_FLOOR);
        assertThat(DesktopPaint.FOG_UNSEEN).isEqualTo("#05070a");
    }

    @Test
    void aClickHitsAPassageAndMissesAWall() {
        DesktopPaint.Layout layout = DesktopPaint.Layout.fit(5, 5, 100, 100);
        double cell = layout.cellSize();
        double wall = layout.wall();
        double cx = layout.x(1) + cell / 2.0;
        double cy = layout.y(1) + cell / 2.0;
        assertThat(DesktopPaint.hitCell(layout, cx, cy)).isEqualTo(new Point(0, 0));
        assertThat(DesktopPaint.hitCell(layout, wall / 2.0, cy))
                .as("the west wall is not a cell")
                .isNull();
        DesktopPaint.Layout wide = DesktopPaint.Layout.fit(5, 5, 200, 100);
        assertThat(DesktopPaint.hitCell(wide, 10, cy))
                .as("the letterbox is not a cell")
                .isNull();
        assertThat(DesktopPaint.hitCell(wide, wide.offsetX() + cx, cy))
                .isEqualTo(new Point(0, 0));
        DesktopPaint.Backing hidpi = DesktopPaint.Backing.of(100, 100, 2, 2);
        assertThat(DesktopPaint.hitCell(layout, hidpi, cx * 2, cy * 2))
                .as("HiDPI local coords are bitmap pixels")
                .isEqualTo(new Point(0, 0));
        assertThat(DesktopPaint.hitCell(null, 10, 10)).isNull();
    }

    @Test
    void aWidePassageGetsTheSameHighlightStripeAsTheWeb() {
        DesktopPaint.Layout roomy = DesktopPaint.Layout.fit(3, 3, 30, 30);
        DesktopPaint.Hairline stripe = DesktopPaint.floorHiStroke(roomy, 1, 1);
        assertThat(roomy.cellSize()).isEqualTo(20.0);
        assertThat(DesktopPaint.FLOOR_HI).isEqualTo("#536272");
        assertThat(stripe).isNotNull();
        assertThat(stripe.w()).isEqualTo(18.0);
        assertThat(stripe.h()).isEqualTo(1.0);
        assertThat(DesktopPaint.floorHi(roomy, 0, 1))
                .as("a wall tile is not a corridor")
                .isFalse();
        DesktopPaint.Layout tight = DesktopPaint.Layout.fit(5, 5, 20, 20);
        assertThat(tight.cellSize()).isLessThan(10);
        assertThat(DesktopPaint.floorHiStroke(tight, 1, 1))
                .as("web skips the highlight when the cell is under 10px")
                .isNull();
        assertThat(DesktopPaint.floorHi(roomy, 1, 1, 0.6))
                .as("fog lamp below 0.7 leaves the floor dim")
                .isFalse();
    }

    @Test
    void hotspotPlacementIsDeterministicAndPaintsAdjacentOpenings() {
        List<Hotspot> a = DesktopPaint.placeSpots(15, 15, 4, 42, 25);
        List<Hotspot> b = DesktopPaint.placeSpots(15, 15, 4, 42, 25);
        List<Hotspot> c = DesktopPaint.placeSpots(15, 15, 4, 43, 25);
        assertThat(a).hasSize(4).isEqualTo(b).isNotEqualTo(c);
        assertThat(DesktopPaint.placeSpots(15, 15, 0, 42, 25)).isEmpty();

        TileType[][] tiles = new TileType[5][5];
        for (int r = 0; r < 5; r++) {
            for (int col = 0; col < 5; col++) {
                tiles[r][col] = (r % 2 == 0 || col % 2 == 0) ? TileType.WALL : TileType.PASSAGE;
            }
        }
        tiles[1][2] = TileType.PASSAGE;
        List<Hotspot> pair = List.of(new Hotspot(0, 0, 25), new Hotspot(0, 1, 25));
        assertThat(DesktopPaint.hotspotOverlay(pair, tiles))
                .contains(
                        new DesktopPaint.TileRect(1, 1),
                        new DesktopPaint.TileRect(1, 3),
                        new DesktopPaint.TileRect(1, 2));
        tiles[1][1] = TileType.WALL;
        assertThat(DesktopPaint.hotspotOverlay(pair, tiles))
                .as("a wall cell is not a hot-spot wash")
                .doesNotContain(new DesktopPaint.TileRect(1, 1));

        assertThat(DesktopPaint.hotspotCellAlpha(0)).isEqualTo(0.2);
        assertThat(DesktopPaint.hotspotCellAlpha(25)).isEqualTo(0.325);
        assertThat(DesktopPaint.hotspotCellAlpha(100)).isEqualTo(0.7);
        assertThat(DesktopPaint.hotspotCellAlpha(200)).isEqualTo(0.7);
        assertThat(DesktopPaint.HOTSPOT_OPENING_ALPHA).isEqualTo(0.35);
        assertThat(DesktopPaint.HOTSPOT).isEqualTo("#e5484d");
        DesktopPaint.HotWash wash = DesktopPaint.hotspotWash(
                List.of(new Hotspot(0, 0, 10), new Hotspot(0, 1, 80)), tiles);
        assertThat(wash.cells()).hasSize(1);
        assertThat(wash.cells().get(0).cost()).isEqualTo(80);
        assertThat(DesktopPaint.hotspotCellAlpha(10))
                .isLessThan(DesktopPaint.hotspotCellAlpha(80));
    }

    @Test
    void aWalkPaintsStoodOnCellsAndTheOpeningBetweenThem() {
        Point a = new Point(0, 0);
        Point b = new Point(0, 1);
        assertThat(DesktopPaint.walkOverlay(List.of(a, b)))
                .as("a walk keeps start underfoot; a solve ribbon would have skipped it")
                .containsExactly(
                        new DesktopPaint.TileRect(1, 1),
                        new DesktopPaint.TileRect(1, 3),
                        new DesktopPaint.TileRect(1, 2));
        assertThat(DesktopPaint.walkOverlay(List.of())).isEmpty();
        assertThat(DesktopPaint.walkOverlay(null)).isEmpty();
    }

    @Test
    void aMissingPathIsNoOverlay() {
        assertThat(DesktopPaint.pathOverlay(null, new Point(0, 0), new Point(1, 1)))
                .isEmpty();
        assertThat(DesktopPaint.pathOverlay(List.of(), new Point(0, 0), new Point(1, 1)))
                .isEmpty();
    }

    @Test
    void thePlayerDiscIsInsetInsideThePassageTile() {
        DesktopPaint.Layout layout = DesktopPaint.Layout.fit(3, 3, 30, 30);
        DesktopPaint.Marker mark = DesktopPaint.playerMarker(layout, new Point(0, 0));
        assertThat(mark).isNotNull();
        assertThat(layout.cellSize()).isEqualTo(20.0);
        assertThat(mark.size())
                .as("inset is 10%% of the passage, so the disc is smaller than the tile")
                .isEqualTo(16.0);
        assertThat(DesktopPaint.playerMarker(layout, null)).isNull();
    }

    @Test
    void arrivingPaintsAGoldRingLargerThanTheGoalDisc() {
        DesktopPaint.Layout layout = DesktopPaint.Layout.fit(3, 3, 30, 30);
        DesktopPaint.Ring ring = DesktopPaint.victoryRing(layout, new Point(0, 0));
        DesktopPaint.Marker goal = DesktopPaint.endpointMarker(layout, new Point(0, 0));
        assertThat(ring).isNotNull();
        assertThat(DesktopPaint.VICTORY_GOLD).isEqualTo("#f0b429");
        assertThat(ring.radius())
                .as("web strokes 0.7·cell around the goal")
                .isEqualTo(layout.cellSize() * 0.7);
        assertThat(ring.radius() * 2).isGreaterThan(goal.size());
        assertThat(ring.width()).isEqualTo(Math.max(2.0, layout.wall()));
        assertThat(DesktopPaint.victoryRing(layout, null)).isNull();
    }

    @Test
    void startAndGoalTilesPaintAsFloorSoTheDiscsCanSitOnTheCorridor() {
        assertThat(DesktopPaint.floorRole(TileType.START)).isEqualTo(TileType.PASSAGE);
        assertThat(DesktopPaint.floorRole(TileType.GOAL)).isEqualTo(TileType.PASSAGE);
        assertThat(DesktopPaint.floorRole(TileType.WALL)).isEqualTo(TileType.WALL);
        assertThat(DesktopPaint.floorRole(null)).isEqualTo(TileType.PASSAGE);
    }

    @Test
    void theEndpointDiscIsSmallerThanThePlayerDisc() {
        DesktopPaint.Layout layout = DesktopPaint.Layout.fit(3, 3, 30, 30);
        DesktopPaint.Marker end = DesktopPaint.endpointMarker(layout, new Point(0, 0));
        DesktopPaint.Marker player = DesktopPaint.playerMarker(layout, new Point(0, 0));
        assertThat(end).isNotNull();
        assertThat(end.size())
                .as("web radius is 0.34·cell, so the disc is 0.68·cell")
                .isCloseTo(13.6, within(1e-9));
        assertThat(end.size()).isLessThan(player.size());
        assertThat(DesktopPaint.endpointMarker(layout, null)).isNull();
        assertThat(DesktopPaint.disc(null, new Point(0, 0), 0.34)).isNull();
    }

    @Test
    void aHiDpiCanvasHasADevicePixelBackingStore() {
        DesktopPaint.Backing store = DesktopPaint.Backing.of(800, 600, 2, 2);
        assertThat(store).isNotNull();
        assertThat(store.cssW()).isEqualTo(800);
        assertThat(store.pixelW()).isEqualTo(1600);
        assertThat(store.pixelH()).isEqualTo(1200);
        assertThat(DesktopPaint.Backing.of(800, 600, 0, 2).scaleX()).isEqualTo(1);
        assertThat(DesktopPaint.Backing.of(0, 600, 2, 2)).isNull();
    }

    @Test
    void anEmptyCanvasHasCopyInsteadOfABlankVoid() {
        assertThat(DesktopPaint.EMPTY_WORDMARK).isEqualTo("DAEDALUS");
        assertThat(DesktopPaint.EMPTY_TITLE).contains("Generate");
        assertThat(DesktopPaint.EMPTY_DETAIL).contains("Solve");
        assertThat(DesktopPaint.EMPTY_HINT).contains("arrow");
    }

    @Test
    void theEmptyMarkIsTheSameMiniatureAsTheWebIdleTiles() {
        assertThat(DesktopPaint.EMPTY_MARK).hasSize(7);
        assertThat(DesktopPaint.EMPTY_MARK[0]).hasSize(11);
        assertThat(DesktopPaint.emptyMarkFloors()).hasSize(28);
        assertThat(DesktopPaint.emptyMarkFloors())
                .contains(
                        new DesktopPaint.TileRect(1, 1),
                        new DesktopPaint.TileRect(5, 9));
        DesktopPaint.Layout mark = DesktopPaint.emptyMarkLayout(400, 300);
        assertThat(mark).isNotNull();
        assertThat(mark.cellSize())
                .as("budget is 132×92 so a large window does not inflate the mark")
                .isEqualTo(20.0);
        assertThat(mark.offsetX())
                .as("centered on the canvas, not left-aligned in the 132px budget")
                .isEqualTo(135.0);
        assertThat(mark.offsetY()).isEqualTo(82.0);
        assertThat(DesktopPaint.endpointMarker(mark, DesktopPaint.EMPTY_MARK_START)).isNotNull();
        assertThat(DesktopPaint.endpointMarker(mark, DesktopPaint.EMPTY_MARK_GOAL)).isNotNull();
        assertThat(DesktopPaint.emptyMarkLayout(0, 300)).isNull();
    }
}
