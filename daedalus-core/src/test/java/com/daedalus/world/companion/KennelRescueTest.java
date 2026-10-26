// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.companion.KennelRescue.Plan;
import com.daedalus.world.companion.KennelRescue.Rescuer;
import com.daedalus.world.companion.KennelRescue.Wreck;
import com.daedalus.world.companion.TonicBottler.Bottle;

import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class KennelRescueTest {
    private static final Optional<Bottle> T3 = Optional.of(new Bottle("calm", TonicBottler.Tier.T3, 600, 0));
    private static final Rescuer TANK = new Rescuer("tank", 85, Optional.empty());
    private static final Rescuer LUNA = new Rescuer("luna", 90, Optional.empty());
    private static final Rescuer PIPPY = new Rescuer("pippy", 60, T3);

    @Test
    void onlyDevotedPetsRescueAndFreshTonicAddsOne() {
        assertThat(KennelRescue.capacity(TANK, 0)).isEqualTo(2);
        assertThat(KennelRescue.capacity(PIPPY, 0)).isZero();
        assertThat(KennelRescue.capacity(new Rescuer("tank", 85, T3), 5)).isEqualTo(3);
        assertThat(KennelRescue.capacity(new Rescuer("tank", 85, T3), 14)).isEqualTo(2);
    }

    @Test
    void planCountsOnlyTripsThatFinishBeforeTheFall() {
        Wreck w = new Wreck("Vega", 10, 5, 2);
        Plan p = KennelRescue.plan(w, List.of(TANK, PIPPY), 0);
        assertThat(p.trips()).isEqualTo(2);
        assertThat(p.perTrip()).isEqualTo(2);
        assertThat(p.saved()).isEqualTo(4);
        assertThat(p.lost()).isEqualTo(6);
        assertThat(p.crew()).containsExactly("tank");
        assertThat(p.leftHome()).containsExactly("pippy");
        assertThat(KennelRescue.shortfallPerTrip(w, p)).isEqualTo(3);
    }

    @Test
    void lastArkBellNeedsThreePerTrip() {
        assertThat(KennelRescue.lastArkBell(List.of(TANK), 0)).isFalse();
        assertThat(KennelRescue.plan(KennelRescue.KEPLER, List.of(TANK), 0).saved()).isEqualTo(8);
        assertThat(KennelRescue.lastArkBell(List.of(new Rescuer("tank", 85, T3)), 2)).isTrue();
        assertThat(KennelRescue.lastArkBell(List.of(TANK, LUNA), 0)).isTrue();
        assertThat(KennelRescue.shortfallPerTrip(KennelRescue.KEPLER,
            KennelRescue.plan(KennelRescue.KEPLER, List.of(TANK, LUNA), 0))).isZero();
    }

    @Test
    void tooFarWreckSavesNoOne() {
        Wreck w = new Wreck("Far", 6, 1, 2);
        Plan p = KennelRescue.plan(w, List.of(TANK, LUNA), 0);
        assertThat(p.trips()).isZero();
        assertThat(p.saved()).isZero();
        assertThat(KennelRescue.shortfallPerTrip(w, p)).isEqualTo(Integer.MAX_VALUE);
    }

    @Test
    void seededWrecksAreDeterministicAndInRange() {
        assertThat(Wreck.seeded("A", 7)).isEqualTo(Wreck.seeded("A", 7));
        for (long s = 0; s < 200; s++) {
            Wreck w = Wreck.seeded("W", s);
            assertThat(w.survivors()).isBetween(4, 12);
            assertThat(w.daysUntilFall()).isBetween(3, 8);
            assertThat(w.tripDays()).isBetween(1, 2);
        }
        assertThatThrownBy(() -> new Wreck("bad", 1, 1, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}