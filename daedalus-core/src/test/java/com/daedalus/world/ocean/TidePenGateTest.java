// SPDX-License-Identifier: MIT
package com.daedalus.world.ocean;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.ocean.TidePenGate.Action;
import com.daedalus.world.ocean.TidePenGate.CareEvent;
import com.daedalus.world.ocean.TidePenGate.Kind;
import com.daedalus.world.ocean.TidePenGate.Rule;
import com.daedalus.world.ocean.TidePenGate.Species;
import com.daedalus.world.ocean.TidePenGate.Subject;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

class TidePenGateTest {

    private static final Species TURTLE = new Species("sea_turtle", Set.of("Seagrass"), Set.of("Seagrass"));
    private static final Subject WHO = new Subject("actor-1", "turtle-7", "sea_turtle", "OCEAN", "spring");
    private static final Rule R = Rule.DEFAULT;

    private static CareEvent e(String id, Kind k, int day, String item) {
        return new CareEvent(id, "actor-1", "turtle-7", k, day, item);
    }

    private static List<CareEvent> settledEvents() {
        return new ArrayList<>(List.of(e("p1", Kind.PLANT, 1, "Seagrass"), e("f1", Kind.FEED, 1, "Seagrass"),
                e("f2", Kind.FEED, 1, "Seagrass"), e("f3", Kind.FEED, 2, "Seagrass")));
    }

    @Test
    void leavingWildAndFeedingAreAlwaysAllowed() {
        assertThat(TidePenGate.allow(Action.LEAVE_WILD, WHO, TURTLE, List.of(), R).allowed()).isTrue();
        assertThat(TidePenGate.allow(Action.FEED, WHO, TURTLE, List.of(e("h", Kind.HARM, 1, null)), R).allowed()).isTrue();
    }

    @Test
    void penningIsRefusedWithNoCare() {
        var d = TidePenGate.allow(Action.ENCLOSE, WHO, TURTLE, List.of(), R);
        assertThat(d.allowed()).isFalse();
        assertThat(d.reason()).startsWith("not settled");
        assertThat(TidePenGate.allow(Action.CAPTURE, WHO, TURTLE, List.of(), R).allowed()).isFalse();
    }

    @Test
    void settledCareAllowsEncloseAndCapture() {
        assertThat(TidePenGate.settled(WHO, TURTLE, settledEvents(), R).allowed()).isTrue();
        assertThat(TidePenGate.allow(Action.ENCLOSE, WHO, TURTLE, settledEvents(), R).allowed()).isTrue();
        assertThat(TidePenGate.allow(Action.CAPTURE, WHO, TURTLE, settledEvents(), R).allowed()).isTrue();
    }

    @Test
    void careTakesTwoDays() {
        var ev = List.of(e("p1", Kind.PLANT, 1, "Seagrass"), e("f1", Kind.FEED, 1, "Seagrass"),
                e("f2", Kind.FEED, 1, "Seagrass"), e("f3", Kind.FEED, 1, "Seagrass"));
        assertThat(TidePenGate.settled(WHO, TURTLE, ev, R).reason()).contains("another day");
    }

    @Test
    void theWrongFoodDoesNotCount() {
        var ev = settledEvents();
        ev.set(3, e("f3", Kind.FEED, 2, "RedDulse"));
        assertThat(TidePenGate.settled(WHO, TURTLE, ev, R).reason()).contains("1 more");
    }

    @Test
    void habitatMustBePlantedFirst() {
        var ev = settledEvents();
        ev.remove(0);
        assertThat(TidePenGate.settled(WHO, TURTLE, ev, R).reason()).contains("habitat");
        ev.add(e("p2", Kind.PLANT, 1, "Bladderwrack"));                // not this species' habitat
        assertThat(TidePenGate.settled(WHO, TURTLE, ev, R).allowed()).isFalse();
    }

    @Test
    void anyHarmBlocksSettling() {
        var ev = settledEvents();
        ev.add(e("h1", Kind.HARM, 2, null));
        var d = TidePenGate.allow(Action.CAPTURE, WHO, TURTLE, ev, R);
        assertThat(d.allowed()).isFalse();
        assertThat(d.reason()).contains("harmed");
    }

    @Test
    void anIdenticalReplayWithinOneCallCountsOnce() {
        var ev = List.of(e("p1", Kind.PLANT, 1, "Seagrass"), e("f1", Kind.FEED, 1, "Seagrass"),
                e("f1", Kind.FEED, 1, "Seagrass"), e("f1", Kind.FEED, 1, "Seagrass"));
        assertThat(TidePenGate.settled(WHO, TURTLE, ev, R).reason()).contains("2 more");
    }

    // ---- review 32524: refuse what cannot be trusted ---------------------------------------------------------

    @Test
    void aConflictingPayloadUnderOneIdIsRefusedSoAHarmCannotHide() {
        var ev = settledEvents();
        ev.add(e("f3", Kind.HARM, 2, null));                         // same id as a feed, different event
        var d = TidePenGate.settled(WHO, TURTLE, ev, R);
        assertThat(d.allowed()).isFalse();
        assertThat(d.reason()).contains("two different events");
    }

    @Test
    void aBlankRequestIdIsRefused() {
        var ev = settledEvents();
        ev.add(e(" ", Kind.FEED, 3, "Seagrass"));
        assertThat(TidePenGate.settled(WHO, TURTLE, ev, R).reason()).contains("no request id");
        ev.set(ev.size() - 1, e(null, Kind.FEED, 3, "Seagrass"));
        assertThat(TidePenGate.settled(WHO, TURTLE, ev, R).allowed()).isFalse();
    }

    @Test
    void careOfAnotherIndividualOrByAnotherActorDoesNotCount() {
        var ev = settledEvents();
        ev.add(new CareEvent("x1", "actor-1", "sheep-3", Kind.FEED, 3, "Seagrass"));   // a herder's sheep is not this turtle
        assertThat(TidePenGate.settled(WHO, TURTLE, ev, R).reason()).contains("another creature");
        var ev2 = settledEvents();
        ev2.add(new CareEvent("x2", "actor-2", "turtle-7", Kind.FEED, 3, "Seagrass"));
        assertThat(TidePenGate.settled(WHO, TURTLE, ev2, R).allowed()).isFalse();
    }

    @Test
    void anIncompleteSubjectOrWrongSpeciesIsRefused() {
        var noSeason = new Subject("actor-1", "turtle-7", "sea_turtle", "OCEAN", "");
        assertThat(TidePenGate.settled(noSeason, TURTLE, settledEvents(), R).reason()).contains("subject incomplete");
        var crab = new Subject("actor-1", "turtle-7", "crab", "OCEAN", "spring");
        assertThat(TidePenGate.settled(crab, TURTLE, settledEvents(), R).allowed()).isFalse();
        assertThat(TidePenGate.settled(null, TURTLE, settledEvents(), R).allowed()).isFalse();
    }

    @Test
    void ruleRangesAreChecked() {
        assertThatThrownBy(() -> new Rule(0, 1, 0, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Rule(3, 4, 0, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Rule(3, 2, -1, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Rule(3, 2, 0, -1)).isInstanceOf(IllegalArgumentException.class);
        assertThat(new Rule(1, 1, 0, 0)).isNotNull();
    }
}
