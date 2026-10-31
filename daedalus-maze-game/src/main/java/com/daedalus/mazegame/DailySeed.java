// SPDX-License-Identifier: MIT

package com.daedalus.mazegame;

import java.time.Clock;
import java.time.LocalDate;
import java.time.ZoneOffset;

/** The Daily seed: the UTC calendar date as yyyymmdd, so every player worldwide shares one maze per day. */
public final class DailySeed {

    private DailySeed() {
    }

    public static long of(LocalDate date) {
        return date.getYear() * 10_000L + date.getMonthValue() * 100L + date.getDayOfMonth();
    }

    public static long today(Clock clock) {
        return of(LocalDate.now(clock.withZone(ZoneOffset.UTC)));
    }
}
