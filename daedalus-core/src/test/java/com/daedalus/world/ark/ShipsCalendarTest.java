// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class ShipsCalendarTest {

    @Test
    void everyDayMatchesJavaTime() {
        LocalDate x = LocalDate.of(1, 1, 1);
        LocalDate end = LocalDate.of(2401, 1, 1);
        while (x.isBefore(end)) {
            int y = x.getYear();
            int m = x.getMonthValue();
            int d = x.getDayOfMonth();
            assertThat(ShipsCalendar.weekday(y, m, d)).isEqualTo(x.getDayOfWeek().getValue());
            assertThat(ShipsCalendar.dayNumber(y, m, d)).isEqualTo(x.toEpochDay());
            assertThat(ShipsCalendar.daysInMonth(y, m)).isEqualTo(x.lengthOfMonth());
            x = x.plusDays(1);
        }
    }

    @Test
    void randomSpansAndEasterBruteForce() {
        SplittableRandom rnd = new SplittableRandom(320);
        for (int t = 0; t < 5000; t++) {
            LocalDate a = LocalDate.ofEpochDay(rnd.nextLong(-700_000, 3_000_000));
            LocalDate b = LocalDate.ofEpochDay(rnd.nextLong(-700_000, 3_000_000));
            assertThat(ShipsCalendar.daysBetween(a.getYear(), a.getMonthValue(), a.getDayOfMonth(),
                    b.getYear(), b.getMonthValue(), b.getDayOfMonth())).isEqualTo(ChronoUnit.DAYS.between(a, b));
        }
        for (int y = 1583; y <= 4099; y++) {
            int e = ShipsCalendar.easter(y);
            LocalDate sun = LocalDate.of(y, e / 100, e % 100);
            assertThat(sun.getDayOfWeek()).isEqualTo(DayOfWeek.SUNDAY);
            assertThat(sun).isBetween(LocalDate.of(y, 3, 22), LocalDate.of(y, 4, 25));
        }
        assertThat(ShipsCalendar.easter(2024)).isEqualTo(331);
        assertThat(ShipsCalendar.easter(2026)).isEqualTo(405);
        assertThat(ShipsCalendar.easter(2285)).isEqualTo(322);
        assertThat(ShipsCalendar.easter(1818)).isEqualTo(322);
        assertThat(ShipsCalendar.easter(2038)).isEqualTo(425);
    }

    @Test
    void questAndGuards() {
        assertThat(ShipsCalendar.QUEST_ID).isEqualTo("q_ships_calendar");
        assertThat(ShipsCalendar.quest(2026, 10, 27, 2)).isTrue();
        assertThat(ShipsCalendar.quest(2026, 10, 27, 3)).isFalse();
        assertThatThrownBy(() -> ShipsCalendar.weekday(2023, 2, 29)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ShipsCalendar.easter(1500)).isInstanceOf(IllegalArgumentException.class);
    }
}