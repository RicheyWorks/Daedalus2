// SPDX-License-Identifier: MIT
package com.daedalus.world.ocean;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.ocean.TidePenGate.Action;
import com.daedalus.world.ocean.TidePenGate.CareEvent;
import com.daedalus.world.ocean.TidePenGate.Kind;
import com.daedalus.world.ocean.TidePenGate.Rule;
import com.daedalus.world.ocean.TidePenGate.Species;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

class TidePenGateTest {

    private static final Species TURTLE = new Species("sea_turtle", Set.of("Seagrass"), Set.of("Seagrass"));
    private static final Rule R = Rule.DEFAULT;

    private static CareEvent e(String id, Kind k, int day, String item) {
        return new CareEvent(id, k, day, item);
    }

    private static List<CareEvent> settledEvents() {
        return new ArrayList<>(List.of(e("p1", Kind.PLANT, 1, "Seagrass"), e("f1", Kind.FEED, 1, "Seagrass"),
                e("f2", Kind.FEED, 1, "Seagrass"), e("f3", Kind.FEED, 2, "Seagrass")));
    }

    @Test
    void leavingWildAndFeedingAreAlwaysAllowed() {
        assertThat(TidePenGate.allow(Action.LEAVE_WILD, TURTLE, List.of(), R).allowed()).isTrue();
        assertThat(TidePenGate.allow(Action.FEED, TURTLE, List.of(e("h", Kind.HARM, 1, null)), R).allowed()).isTrue();
    }

    @Test
    void penningIsRefusedWithNoCare() {
        var d = TidePenGate.allow(Action.ENCLOSE, TURTLE, List.of(), R);
        assertThat(d.allowed()).isFalse();
        assertThat(d.reason()).startsWith("not settled");
        assertThat(TidePenGate.allow(Action.CAPTURE, TURTLE, List.of(), R).allowed()).isFalse();
    }

    @Test
    void settledCareAllowsEncloseAndCapture() {
        assertThat(TidePenGate.settled(TURTLE, settledEvents(), R).allowed()).isTrue();
        assertThat(TidePenGate.allow(Action.ENCLOSE, TURTLE, settledEvents(), R).allowed()).isTrue();
        assertThat(TidePenGate.allow(Action.CAPTURE, TURTLE, settledEvents(), R).allowed()).isTrue();
    }

    @Test
    void careTakesTwoDays() {
        var ev = List.of(e("p1", Kind.PLANT, 1, "Seagrass"), e("f1", Kind.FEED, 1, "Seagrass"),
                e("f2", Kind.FEED, 1, "Seagrass"), e("f3", Kind.FEED, 1, "Seagrass"));
        var d = TidePenGate.settled(TURTLE, ev, R);
        assertThat(d.allowed()).isFalse();
        assertThat(d.reason()).contains("another day");
    }

    @Test
    void theWrongFoodDoesNotCount() {
        var ev = settledEvents();
        ev.set(3, e("f3", Kind.FEED, 2, "RedDulse"));
        assertThat(TidePenGate.settled(TURTLE, ev, R).reason()).contains("1 more");
    }

    @Test
    void habitatMustBePlantedFirst() {
        var ev = settledEvents();
        ev.remove(0);
        assertThat(TidePenGate.settled(TURTLE, ev, R).reason()).contains("habitat");
        ev.add(e("p2", Kind.PLANT, 1, "Bladderwrack"));                // not this species' habitat
        assertThat(TidePenGate.settled(TURTLE, ev, R).allowed()).isFalse();
    }

    @Test
    void anyHarmBlocksSettling() {
        var ev = settledEvents();
        ev.add(e("h1", Kind.HARM, 2, null));
        var d = TidePenGate.allow(Action.CAPTURE, TURTLE, ev, R);
        assertThat(d.allowed()).isFalse();
        assertThat(d.reason()).contains("harmed");
    }

    @Test
    void aReplayedRequestCountsOnce() {
        var ev = List.of(e("p1", Kind.PLANT, 1, "Seagrass"), e("f1", Kind.FEED, 1, "Seagrass"),
                e("f1", Kind.FEED, 2, "Seagrass"), e("f1", Kind.FEED, 2, "Seagrass"));
        assertThat(TidePenGate.settled(TURTLE, ev, R).allowed()).isFalse();
    }
}
