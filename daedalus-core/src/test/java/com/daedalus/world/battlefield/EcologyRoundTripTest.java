// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import org.junit.jupiter.api.Test;

/**
 * Java -> C++ -> Java without Unreal (ADR-061). Java's DBE 1 snapshot of BattlefieldDemo.scene(7) is the fixture
 * engines/unreal/core-test/ecology_core_test.cpp reads; the DBE-E 1 IGNITE it writes is the events fixture this test
 * applies. If either side changes its format, one of the two tests fails.
 */
class EcologyRoundTripTest {

    private static final Path DIR = Path.of("..", "engines", "unreal", "core-test");

    private static String read(String name) throws IOException {
        return Files.readString(DIR.resolve(name)).replace("\r", "");
    }

    @Test
    void javaStillWritesTheSnapshotTheCppReads() throws IOException {
        assertThat(Dbe.write(BattlefieldDemo.scene(7))).isEqualTo(read("ecology_roundtrip.dbe"));
    }

    @Test
    void javaAnswersLikeTheCppAtTheCheckPoints() throws IOException {
        BattlefieldEcology e = Dbe.read(read("ecology_roundtrip.dbe"));
        assertThat(e.coverAt(900, 1500)).isEqualTo(0.05);
        assertThat(e.at(900, 1500).concealment()).isEqualTo(0.35);
        assertThat(e.coverAt(2000, 1500)).isEqualTo(0.80);
        assertThat(e.at(2000, 1500).concealment()).isEqualTo(0.60);
        assertThat(e.burningAt(2000, 1500)).isFalse();
    }

    @Test
    void javaAppliesTheIgniteTheCppWrote() throws IOException {
        BattlefieldEcology e = Dbe.read(read("ecology_roundtrip.dbe"));
        List<Dbe.Event> events = Dbe.readEvents(read("ecology_roundtrip_events.txt"));
        assertThat(events).containsExactly(new Dbe.Event(BattlefieldEcology.EventKind.IGNITE, 2000, 1500, 0, 150));
        assertThat(Dbe.apply(e, events)).isPositive();
        assertThat(e.burningAt(2000, 1500)).isTrue();
        assertThat(e.burningAt(900, 1500)).isFalse();
    }
}