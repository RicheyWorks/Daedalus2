// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.KilnBookings.Grade;
import com.daedalus.world.forge.KilnBookings.Plan;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class KilnBookingsTest {

    private static long brute(int[][] req) {
        long best = 0;
        for (int mask = 0; mask < (1 << req.length); mask++) {
            List<Integer> pick = new ArrayList<>();
            for (int i = 0; i < req.length; i++) {
                if ((mask >> i & 1) == 1) {
                    pick.add(i);
                }
            }
            best = Math.max(best, KilnBookings.pay(req, pick));
        }
        return best;
    }

    @Test
    void bestMatchesBruteForceOnSeededDays() {
        for (long seed = 1; seed <= 300; seed++) {
            int[][] req = KilnBookings.requests(seed, 1 + (int) (seed % 13), 6 + (int) (seed % 12));
            Plan p = KilnBookings.best(req);
            assertThat(p.pay()).as("seed %d", seed).isEqualTo(brute(req));
            assertThat(KilnBookings.pay(req, p.accepted())).isEqualTo(p.pay());
        }
    }

    @Test
    void greediesNeverBeatBestAndBothLose() {
        int lossEnd = 0;
        int lossPay = 0;
        for (long seed = 1; seed <= 300; seed++) {
            int[][] req = KilnBookings.requests(seed * 11L, 10, 16);
            long b = KilnBookings.best(req).pay();
            long e = KilnBookings.earliestEnd(req).pay();
            long h = KilnBookings.highestPay(req).pay();
            assertThat(e).isLessThanOrEqualTo(b).isNotNegative();
            assertThat(h).isLessThanOrEqualTo(b).isNotNegative();
            lossEnd += e < b ? 1 : 0;
            lossPay += h < b ? 1 : 0;
        }
        assertThat(lossEnd).isPositive();
        assertThat(lossPay).isPositive();
    }

    @Test
    void handWorkedDay() {
        int[][] req = {{0, 4, 5}, {4, 8, 5}, {2, 6, 9}, {0, 8, 11}};
        assertThat(KilnBookings.best(req).pay()).isEqualTo(11);
        assertThat(KilnBookings.best(req).accepted()).containsExactly(3);
        assertThat(KilnBookings.highestPay(req).pay()).isEqualTo(11);
        assertThat(KilnBookings.earliestEnd(req).pay()).isEqualTo(10);
        int[][] touch = {{0, 5, 3}, {5, 9, 4}};
        assertThat(KilnBookings.best(touch).pay()).isEqualTo(7);
        assertThat(KilnBookings.pay(req, List.of(0, 2))).isEqualTo(-1);
    }

    @Test
    void sameSeedReplays() {
        assertThat(KilnBookings.requests(207L, 9, 16)).isDeepEqualTo(KilnBookings.requests(207L, 9, 16));
        assertThat(KilnBookings.best(KilnBookings.requests(207L, 9, 16)))
                .isEqualTo(KilnBookings.best(KilnBookings.requests(207L, 9, 16)));
        assertThat(KilnBookings.QUEST_ID).isEqualTo("q_kiln_bookings");
    }

    @Test
    void gradesLinesAndRejects() {
        assertThat(KilnBookings.grade(100, 100)).isEqualTo(Grade.FULL_KILN);
        assertThat(KilnBookings.grade(90, 100)).isEqualTo(Grade.WARM);
        assertThat(KilnBookings.grade(89, 100)).isEqualTo(Grade.COLD);
        assertThatThrownBy(() -> KilnBookings.grade(101, 100)).isInstanceOf(IllegalArgumentException.class);
        assertThat(KilnBookings.forgemasterLine(new Plan(List.of(), 0), 10)).contains("cold");
        assertThat(KilnBookings.best(new int[0][]).pay()).isZero();
        assertThatThrownBy(() -> KilnBookings.best(new int[][] {{3, 3, 1}}))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
