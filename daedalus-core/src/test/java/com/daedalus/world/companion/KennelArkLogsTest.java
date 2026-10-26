// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.companion.KennelArkLogs.Fragment;
import com.daedalus.world.companion.KennelArkLogs.Hunt;
import com.daedalus.world.companion.KennelGrowth.Pup;

import java.util.List;

import org.junit.jupiter.api.Test;

class KennelArkLogsTest {
    static final Pup ADULT = new Pup("tank", 30, 25, 85, 0);
    static final Pup JUVENILE = new Pup("pip", 12, 12, 60, 0);

    @Test
    void scatterIsSeededAndComplete() {
        List<Fragment> f = KennelArkLogs.scatter(7L);
        assertThat(f).hasSize(6).isEqualTo(KennelArkLogs.scatter(7L));
        assertThat(f.stream().map(Fragment::arkDay).sorted().toList()).containsExactly(1, 2, 3, 4, 5, 6);
        assertThat(f).allMatch(x -> x.distance() >= 1 && x.distance() <= 9);
        assertThatThrownBy(() -> new Fragment(7, 1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void scentNeedsGrowthAndBond() {
        assertThat(KennelArkLogs.canScent(new Pup("p", 4, 4, 90, 0), 1)).isFalse();
        assertThat(KennelArkLogs.canScent(new Pup("p", 30, 25, 30, 0), 1)).isFalse();
        assertThat(KennelArkLogs.canScent(JUVENILE, 6)).isTrue();
        assertThat(KennelArkLogs.canScent(JUVENILE, 7)).isFalse();
        assertThat(KennelArkLogs.canScent(ADULT, 14)).isTrue();
        assertThat(KennelArkLogs.hunt(new Pup("p", 4, 4, 90, 0), KennelArkLogs.scatter(1), List.of()).failReason())
            .isEqualTo("too young");
        assertThat(KennelArkLogs.hunt(new Pup("p", 30, 25, 10, 0), KennelArkLogs.scatter(1), List.of()).failReason())
            .isEqualTo("bond too low");
    }

    @Test
    void orderMattersAgainstTheDrift() {
        List<Fragment> f = List.of(new Fragment(1, 1), new Fragment(2, 1), new Fragment(3, 1), new Fragment(4, 1),
            new Fragment(5, 1), new Fragment(6, 6));
        Hunt nearFirst = KennelArkLogs.hunt(JUVENILE, f, List.of(0, 1, 2, 3, 4, 5));
        assertThat(nearFirst.complete()).isFalse();
        assertThat(nearFirst.failReason()).contains("1");
        Hunt planned = KennelArkLogs.hunt(JUVENILE, f, KennelArkLogs.plan(JUVENILE, f));
        assertThat(planned.complete()).isTrue();
        assertThat(planned.pages()).hasSize(6).first().asString().startsWith("Day 1");
        assertThat(planned.foundDays()).containsExactly(1, 2, 3, 4, 5, 6);
    }

    @Test
    void anAdultHoundBringsTheLogHome() {
        for (long s = 0; s < 50; s++) {
            List<Fragment> f = KennelArkLogs.scatter(s);
            Hunt h = KennelArkLogs.hunt(ADULT, f, KennelArkLogs.plan(ADULT, f));
            assertThat(h.complete()).as("seed " + s).isTrue();
            assertThat(h.daysUsed()).isLessThanOrEqualTo(KennelArkLogs.QUEST_DAYS);
        }
    }
}