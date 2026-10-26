// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.WeightedMazeGrid;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

import static org.assertj.core.api.Assertions.assertThat;

class ExploreSupportTest {

    @Test
    void liveAndTrafficRefuseNullGrids() {
        assertThat(ExploreLive.pulse(null, 1L, false)).isNull();
        assertThat(ExploreTraffic.wrap(null)).isNull();
        assertThat(ExploreTraffic.occupy(null, new Point(0, 0))).isNull();
    }

    @Test
    void wrapDoesNotDoubleWrap() {
        WeightedMazeGrid weighted = new WeightedMazeGrid(2, 2);
        assertThat(ExploreTraffic.wrap(weighted)).isSameAs(weighted);
        MazeGrid plain = new MazeGrid(2, 2);
        assertThat(ExploreTraffic.wrap(plain)).isInstanceOf(WeightedMazeGrid.class);
    }

    @Test
    void sessionIgnoresAStationaryStep() {
        ExploreSession session = new ExploreSession();
        session.record(new Point(0, 0), new Point(0, 0));
        session.record(null, new Point(0, 1));
        assertThat(session.steps()).isEmpty();
        assertThat(session.moveJson(null)).isEqualTo("{\"to\":null}");
    }

    @Test
    void replaceKeepsALegalBody() {
        MazeGrid first = new MazeGrid(2, 2);
        first.carve(first.cell(0, 0), Direction.EAST);
        ExploreWorld world = new ExploreWorld("test", 1L, first);
        MazeGrid next = first.copy();
        world.replace(next);
        assertThat(world.body().cell()).isEqualTo(first.start());
        world.replace(null);
        assertThat(world.grid()).isSameAs(next);
    }

    @Test
    void mainPrintsStoryWithoutAWindow() {
        PrintStream old = System.out;
        ByteArrayOutputStream buf = new ByteArrayOutputStream();
        System.setOut(new PrintStream(buf));
        try {
            ExploreLauncher.main(new String[0]);
        } finally {
            System.setOut(old);
        }
        assertThat(buf.toString()).contains("\"generator\":\"dungeon\"");
    }

    @Test
    void intentPlusAndPitchFloor() {
        ExploreInput.Intent sum = ExploreInput.Intent.none().plus(new ExploreInput.Intent(1, 0, 0, 0));
        assertThat(sum.forward()).isEqualTo(1);
        assertThat(ExploreInput.Intent.none().plus(null).forward()).isZero();
        ExploreBody body = new ExploreBody(0, 0, 0, 0);
        body.look(0, -10);
        assertThat(body.pitch()).isEqualTo(-ExploreBody.PITCH_LIMIT);
        ExploreInput.applyLook(null, sum);
        ExploreInput.applyLook(body, null);
        assertThat(ExploreInput.moveVector(null, sum, 1)[0]).isZero();
    }

    @Test
    void storyEscapesBreaks() {
        assertThat(ExploreStory.escape("a\nb\rc")).isEqualTo("a\\nb\\rc");
        assertThat(ExploreMarkers.plan(null)).isEmpty();
    }
}
