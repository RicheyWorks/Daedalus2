// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.companion.KennelBond.Care;
import com.daedalus.world.companion.KennelBond.QuestResult;
import com.daedalus.world.companion.KennelBond.Rules;
import com.daedalus.world.companion.KennelBond.Tier;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class KennelBondTest {
    private static final Rules R = Rules.defaults();
    private static final Care FULL = new Care(true, true, true, 5);
    private static final Care BASIC = new Care(true, true, false, 0);
    private static final Care DRY = new Care(true, false, false, 3);

    @Test
    void fullCareAndBasicCareGains() {
        assertThat(KennelBond.step(10, FULL, R)).isEqualTo(23);
        assertThat(KennelBond.step(10, BASIC, R)).isEqualTo(15);
        assertThat(KennelBond.step(10, new Care(true, true, false, 40), R)).isEqualTo(20);
    }

    @Test
    void neglectDayPenalizesAndIgnoresGains() {
        assertThat(DRY.neglected()).isTrue();
        assertThat(KennelBond.step(30, DRY, R)).isEqualTo(19);
        assertThat(KennelBond.step(5, new Care(false, true, true, 5), R)).isZero();
    }

    @Test
    void bondIsClampedToMax() {
        assertThat(KennelBond.step(99, FULL, R)).isEqualTo(100);
        assertThat(KennelBond.run(150, List.of(), R)).containsExactly(100);
    }

    @Test
    void tiersGateCommands() {
        assertThat(Tier.of(0)).isEqualTo(Tier.WARY);
        assertThat(Tier.of(25)).isEqualTo(Tier.FAMILIAR);
        assertThat(Tier.of(79)).isEqualTo(Tier.LOYAL);
        assertThat(Tier.of(80)).isEqualTo(Tier.DEVOTED);
        assertThat(KennelBond.obeys(24, "come")).isFalse();
        assertThat(KennelBond.obeys(50, "fetch")).isTrue();
        assertThat(KennelBond.obeys(79, "rescue")).isFalse();
        assertThat(KennelBond.obeys(80, "rescue")).isTrue();
    }

    @Test
    void pairReadyNeedsBothFamiliar() {
        assertThat(KennelBond.pairReady(25, 60)).isTrue();
        assertThat(KennelBond.pairReady(24, 90)).isFalse();
    }

    @Test
    void keepersMarkPassesWithFullCareFailsOnFoodAndWaterOnly() {
        QuestResult ok = KennelBond.keepersMark(Collections.nCopies(7, FULL), R);
        assertThat(ok.complete()).isTrue();
        assertThat(ok.dayReached()).isEqualTo(4);
        assertThat(ok.trail()).containsExactly(10, 23, 36, 49, 62);
        QuestResult basic = KennelBond.keepersMark(Collections.nCopies(7, BASIC), R);
        assertThat(basic.complete()).isFalse();
        assertThat(basic.failReason()).contains("not loyal");
        assertThat(basic.trail()).last().isEqualTo(45);
    }

    @Test
    void keepersMarkFailsOnAnyNeglectDay() {
        QuestResult r = KennelBond.keepersMark(List.of(FULL, FULL, DRY, FULL, FULL), R);
        assertThat(r.complete()).isFalse();
        assertThat(r.failReason()).isEqualTo("neglect on day 3");
        assertThat(r.trail()).containsExactly(10, 23, 36, 25);
    }

    @Test
    void careFromPantryReadsHungryList() {
        KennelPantry.State st = new KennelPantry.State(0, 0, Map.of("tank", 0, "luna", 1));
        KennelPantry.DayReport day = new KennelPantry.DayReport(st, 2.0, 0.0, 1, 1,
            List.of("tank", "luna"), List.of("luna"));
        assertThat(KennelBond.careFromPantry(day, "tank", true, false, 2)).isEqualTo(new Care(true, true, false, 2));
        assertThat(KennelBond.careFromPantry(day, "luna", true, false, 2).neglected()).isTrue();
        assertThat(KennelBond.careFromPantry(day, "ghost", true, false, 0).fed()).isFalse();
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> new Care(true, true, false, -1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Rules(4, 2, 3, 1, 5, 10, 1, 50, 10, 7))
            .isInstanceOf(IllegalArgumentException.class);
    }
}