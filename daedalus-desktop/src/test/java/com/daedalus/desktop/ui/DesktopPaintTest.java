// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.model.Point;
import com.daedalus.model.TileType;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Canvas geometry without a JavaFX toolkit. {@code MainController#redraw}
 * used to be the only copy of these rules, and nothing tested them.
 */
class DesktopPaintTest {

    @Test
    void aSquareCanvasUsesTheFullWidthAndAWideCanvasLetterboxes() {
        DesktopPaint.Layout square = DesktopPaint.Layout.fit(5, 5, 100, 100);
        assertThat(square)
                .as("a 5×5 tile grid in 100×100 should fill the canvas")
                .isNotNull();
        assertThat(square.cellSize()).isEqualTo(20.0);
        assertThat(square.offsetX()).isZero();
        assertThat(square.offsetY()).isZero();

        DesktopPaint.Layout wide = DesktopPaint.Layout.fit(5, 5, 200, 100);
        assertThat(wide.cellSize())
                .as("the short axis owns cell size so the maze is not stretched")
                .isEqualTo(20.0);
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
        assertThat(mark.size())
                .as("inset is 10%% of the cell, so the disc is smaller than the tile")
                .isEqualTo(8.0);
        assertThat(DesktopPaint.playerMarker(layout, null)).isNull();
        assertThat(DesktopPaint.roleFor(null)).isEqualTo(TileType.PASSAGE);
        assertThat(DesktopPaint.roleFor(TileType.WALL)).isEqualTo(TileType.WALL);
    }
}
