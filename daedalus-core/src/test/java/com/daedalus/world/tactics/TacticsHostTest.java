// SPDX-License-Identifier: MIT

package com.daedalus.world.tactics;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.tactics.TacticsHost.Result;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

class TacticsHostTest {
    @Test
    void rejectedRequestsAndOlderOtherSquadsCannotRewindPlayerObservations() {
        var positions = new java.util.ArrayList<TacticalOrders.Vec>();
        TacticsHost host = TacticsHost.withContext((r, p) -> {
            positions.add(p);
            return SquadDirector.decide(r.squad(), r.tick(), r.toUnits(), p);
        });
        host.decide(roster("s", "a", 5), PLAYER);
        String old = "DTE 1\ntick 4\nevent PLAYER player 999 0 0 90\n";
        host.decide(roster("s", "a", 4), old);
        host.decide(roster("s", "a", 5), old);
        host.decide(roster("s", "b", 4), old);
        host.decide(roster("s", "a", 6), "");
        assertThat(positions).hasSize(3).allMatch(p -> p.x() == 0);
    }

    @Test
    void failedBrainDoesNotPublishPlayerStateOrReceipt() {
        var fail = new java.util.concurrent.atomic.AtomicBoolean(true);
        TacticsHost host = TacticsHost.withContext((r, p) -> {
            if (fail.getAndSet(false)) throw new IllegalStateException("store unavailable");
            return SquadDirector.decide(r.squad(), r.tick(), r.toUnits(), p);
        });
        assertThatThrownBy(() -> host.decide(roster("s", "a", 5), PLAYER)).isInstanceOf(IllegalStateException.class);
        assertThat(host.squads()).isZero();
        assertThat(host.decide(roster("s", "a", 5), "").why()).contains("no PLAYER");
    }


    private static String roster(String session, String squad, long tick) {
        return "DTR 1\nsession " + session + " squad " + squad + " tick " + tick + "\n"
                + "unit a SLIME 60.0 60.0 100.0 0.0 0.0 1\n"
                + "unit b SLIME 10.0 60.0 300.0 50.0 0.0 1\n"
                + "unit c SLIME 60.0 60.0 -200.0 80.0 0.0 0\n";
    }

    private static final String PLAYER = "DTE 1\ntick 5\nevent PLAYER player 0.0 0.0 0.0 90.0\n";

    @Test
    void decidesWithTheBaselineAndTheSameBytesAsCallingItDirectly() {
        TacticsHost host = new TacticsHost();
        TacticsHost.Decision d = host.decide(roster("s1", "pack", 5), PLAYER);
        assertThat(d.result()).isEqualTo(Result.APPLY);
        String direct = TacticalOrders.write(SquadDirector.decide("pack", 5,
                TacticalOrders.parseRoster(roster("s1", "pack", 5)).toUnits(), new TacticalOrders.Vec(0, 0, 0)));
        assertThat(d.spec()).isEqualTo(direct);
        assertThat(TacticalOrders.parse(d.spec()).ok()).isTrue();
    }

    @Test
    void fencesTicksPerSessionAndSquad() {
        AtomicInteger calls = new AtomicInteger();
        TacticsHost host = new TacticsHost((sq, t, u, p) -> {
            calls.incrementAndGet();
            return SquadDirector.decide(sq, t, u, p);
        });
        TacticsHost.Decision first = host.decide(roster("s1", "pack", 5), PLAYER);
        TacticsHost.Decision again = host.decide(roster("s1", "pack", 5), "");
        assertThat(again.result()).isEqualTo(Result.REPEAT);
        assertThat(again.spec()).isEqualTo(first.spec());
        assertThat(host.decide(roster("s1", "pack", 4), "").result()).isEqualTo(Result.STALE);
        assertThat(host.decide(roster("s1", "pack", 4), "").spec()).isEmpty();
        assertThat(host.decide(roster("s1", "pack", 6), "").result()).isEqualTo(Result.APPLY);
        assertThat(host.decide(roster("s1", "other", 1), "").result()).as("another squad has its own ticks")
                .isEqualTo(Result.APPLY);
        assertThat(host.decide(roster("s2", "pack", 1), PLAYER).result()).as("a new session starts fresh")
                .isEqualTo(Result.APPLY);
        assertThat(calls.get()).isEqualTo(4);
    }

    @Test
    void withNoPlayerSightingEveryoneHoldsAndTheBrainIsNotAsked() {
        TacticsHost host = new TacticsHost((sq, t, u, p) -> {
            throw new AssertionError("brain asked without a player");
        });
        TacticsHost.Decision d = host.decide(roster("s9", "pack", 1), "DTE 1\ntick 1\n");
        assertThat(d.result()).isEqualTo(Result.APPLY);
        TacticalOrders.ParseResult r = TacticalOrders.parse(d.spec());
        assertThat(r.spec().orders()).hasSize(3).allMatch(o -> o.verb() == TacticalOrders.Verb.HOLD);
        assertThat(r.spec().orders().get(0).at()).isEqualTo(new TacticalOrders.Vec(100, 0, 0));
    }

    @Test
    void thePlayerIsRememberedPerSession() {
        TacticsHost host = new TacticsHost();
        host.decide(roster("s1", "pack", 1), PLAYER);
        TacticsHost.Decision later = host.decide(roster("s1", "pack", 2), "");
        assertThat(TacticalOrders.parse(later.spec()).spec().orders()).anyMatch(o -> o.verb() != TacticalOrders.Verb.HOLD);
        TacticsHost.Decision elsewhere = host.decide(roster("s2", "pack", 2), "");
        assertThat(TacticalOrders.parse(elsewhere.spec()).spec().orders()).allMatch(o -> o.verb() == TacticalOrders.Verb.HOLD);
    }

    @Test
    void badInputIsRefusedBeforeAnythingIsRemembered() {
        TacticsHost host = new TacticsHost();
        assertThatThrownBy(() -> host.decide("DTR 2\n", PLAYER)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> host.decide(roster("s1", "pack", 3), "DTE 1\ntick 1\nevent JUMP a 0 0 0 0\n"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThat(host.squads()).isZero();
        assertThat(host.decide(roster("s1", "pack", 3), PLAYER).result()).isEqualTo(Result.APPLY);
    }

    @Test
    void memoryIsBounded() {
        TacticsHost host = new TacticsHost();
        for (int i = 0; i < TacticsHost.MAX_SQUADS + 50; i++) {
            host.decide(roster("s1", "sq" + i, 1), "");
        }
        assertThat(host.squads()).isEqualTo(TacticsHost.MAX_SQUADS);
    }
}
