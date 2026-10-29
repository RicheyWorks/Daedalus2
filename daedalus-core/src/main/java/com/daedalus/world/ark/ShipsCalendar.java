// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G320 The Ship's Calendar: the log keeper names the weekday of any proleptic Gregorian date with
 * Zeller's congruence, counts days between dates from a civil day number, and finds the spring
 * feast day with the anonymous Gregorian computus.
 */
public final class ShipsCalendar {

    public static final String QUEST_ID = "q_ships_calendar";

    private ShipsCalendar() { }

    public static boolean isLeap(int year) {
        return (year % 4 == 0 && year % 100 != 0) || year % 400 == 0;
    }

    public static int daysInMonth(int year, int month) {
        if (month < 1 || month > 12) {
            throw new IllegalArgumentException("month " + month);
        }
        if (month == 2) {
            return isLeap(year) ? 29 : 28;
        }
        return (month == 4 || month == 6 || month == 9 || month == 11) ? 30 : 31;
    }

    private static void check(int year, int month, int day) {
        if (year < 1 || year > 999_999) {
            throw new IllegalArgumentException("year " + year);
        }
        if (day < 1 || day > daysInMonth(year, month)) {
            throw new IllegalArgumentException("day " + day);
        }
    }

    /** ISO weekday by Zeller's congruence: 1 = Monday .. 7 = Sunday. */
    public static int weekday(int year, int month, int day) {
        check(year, month, day);
        int m = month;
        int y = year;
        if (m < 3) {
            m += 12;
            y -= 1;
        }
        int k = y % 100;
        int j = y / 100;
        int h = (day + 13 * (m + 1) / 5 + k + k / 4 + j / 4 + 5 * j) % 7;
        return (h + 5) % 7 + 1;
    }

    /** Days since 1970-01-01 (negative before it). */
    public static long dayNumber(int year, int month, int day) {
        check(year, month, day);
        long y = month <= 2 ? year - 1L : year;
        long era = Math.floorDiv(y, 400);
        long yoe = y - era * 400;
        long mp = (month + 9) % 12;
        long doy = (153 * mp + 2) / 5 + day - 1;
        long doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
        return era * 146_097 + doe - 719_468;
    }

    public static long daysBetween(int y1, int m1, int d1, int y2, int m2, int d2) {
        return dayNumber(y2, m2, d2) - dayNumber(y1, m1, d1);
    }

    /** Gregorian Easter Sunday encoded as month * 100 + day. */
    public static int easter(int year) {
        if (year < 1583 || year > 999_999) {
            throw new IllegalArgumentException("year " + year);
        }
        int a = year % 19;
        int b = year / 100;
        int c = year % 100;
        int d = b / 4;
        int e = b % 4;
        int f = (b + 8) / 25;
        int g = (b - f + 1) / 3;
        int h = (19 * a + b - d - g + 15) % 30;
        int i = c / 4;
        int k = c % 4;
        int l = (32 + 2 * e + 2 * i - h - k) % 7;
        int m = (a + 11 * h + 22 * l) / 451;
        int month = (h + l - 7 * m + 114) / 31;
        int day = (h + l - 7 * m + 114) % 31 + 1;
        return month * 100 + day;
    }

    /** Quest q_ships_calendar: name the ISO weekday (1..7) of the landfall date. */
    public static boolean quest(int year, int month, int day, int answer) {
        return weekday(year, month, day) == answer;
    }
}