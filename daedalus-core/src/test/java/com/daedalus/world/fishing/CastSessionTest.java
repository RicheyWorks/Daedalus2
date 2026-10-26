// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.fishing.CastSession.Outcome;
import com.daedalus.world.fishing.CastSession.Phase;
import org.junit.jupiter.api.Test;

class CastSessionTest {

    private final FishTable pond = FishTestData.prism();

    @Test
    void waitsThenBitesThenLandsOnAStrike() {
        CastSession c = new CastSession(pond, Conditions.DAY, 7, 0);
        assertThat(c.waitSeconds()).isBetween(CastSession.MIN_WAIT, CastSession.MIN_WAIT + CastSession.WAIT_SPREAD);
        assertThat(c.phase()).isEqualTo(Phase.WAIT);
        assertThat(c.fish()).isEmpty();
        assertThat(c.biteRemaining()).isZero();
        c.tick(c.waitSeconds() / 2);
        assertThat(c.phase()).isEqualTo(Phase.WAIT);
        c.tick(c.waitSeconds());
        assertThat(c.phase()).isEqualTo(Phase.BITE);
        assertThat(c.fish()).isPresent();
        assertThat(c.biteRemaining()).isEqualTo(c.fish().orElseThrow().windowSeconds());
        assertThat(c.outcome()).isEqualTo(Outcome.NONE);
        assertThat(c.strike()).isEqualTo(Outcome.CAUGHT);
        assertThat(c.phase()).isEqualTo(Phase.DONE);
        assertThat(c.strike()).isEqualTo(Outcome.CAUGHT);
        assertThat(c.reelIn()).isEqualTo(Outcome.CAUGHT);
        c.tick(5);
        assertThat(c.outcome()).isEqualTo(Outcome.CAUGHT);
        assertThat(c.conditions()).isEqualTo(Conditions.DAY);
    }

    @Test
    void strikingTooSoonScattersTheRipple() {
        CastSession c = new CastSession(pond, Conditions.DAY, 7, 1);
        c.tick(0.5);
        assertThat(c.strike()).isEqualTo(Outcome.TOO_SOON);
        assertThat(c.fish()).isEmpty();
    }

    @Test
    void anIgnoredBiteGetsAway() {
        CastSession c = new CastSession(pond, Conditions.DAY, 7, 2);
        c.tick(c.waitSeconds());
        double w = c.fish().orElseThrow().windowSeconds();
        c.tick(w);
        assertThat(c.phase()).isEqualTo(Phase.BITE);
        c.tick(0.001);
        assertThat(c.outcome()).isEqualTo(Outcome.GOT_AWAY);
        assertThat(c.strike()).isEqualTo(Outcome.GOT_AWAY);
    }

    @Test
    void reelingInEndsItEmptyHanded() {
        CastSession c = new CastSession(pond, Conditions.DAY, 7, 3);
        assertThat(c.reelIn()).isEqualTo(Outcome.REELED_IN);
        CastSession d = new CastSession(pond, Conditions.DAY, 7, 3);
        d.tick(d.waitSeconds());
        assertThat(d.reelIn()).isEqualTo(Outcome.REELED_IN);
    }

    @Test
    void sameSeedAndCastReplayExactly() {
        for (int i = 0; i < 50; i++) {
            CastSession a = new CastSession(pond, Conditions.NIGHT, 99, i);
            CastSession b = new CastSession(pond, Conditions.NIGHT, 99, i);
            a.tick(a.waitSeconds());
            b.tick(b.waitSeconds());
            assertThat(a.waitSeconds()).isEqualTo(b.waitSeconds());
            assertThat(a.fish()).isEqualTo(b.fish());
        }
        assertThat(new CastSession(pond, Conditions.DAY, 99, 0).waitSeconds())
                .isNotEqualTo(new CastSession(pond, Conditions.DAY, 99, 1).waitSeconds());
    }

    @Test
    void stormBitesComeSoonerAndShorter() {
        CastSession calm = new CastSession(pond, Conditions.DAY, 5, 4);
        CastSession storm = new CastSession(pond, Conditions.STORM, 5, 4);
        assertThat(storm.waitSeconds()).isEqualTo(calm.waitSeconds() * Conditions.STORM_WAIT_FACTOR);
        storm.tick(storm.waitSeconds());
        assertThat(storm.biteRemaining()).isLessThan(storm.fish().orElseThrow().windowSeconds());
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> new CastSession(null, Conditions.DAY, 1, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CastSession(pond, null, 1, 0)).isInstanceOf(IllegalArgumentException.class);
        CastSession c = new CastSession(pond, Conditions.DAY, 1, 0);
        assertThatThrownBy(() -> c.tick(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> c.tick(Double.NaN)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> c.tick(Double.POSITIVE_INFINITY)).isInstanceOf(IllegalArgumentException.class);
    }
}
