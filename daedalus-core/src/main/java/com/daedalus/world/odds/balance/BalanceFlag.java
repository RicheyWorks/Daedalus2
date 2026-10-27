// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.balance;

/** Why a difficulty mode looks unfair. */
public enum BalanceFlag {
    /** The whole 95% interval sits below the band's floor: too hard. */
    TOO_HARD,
    /** The whole 95% interval sits above the band's ceiling: too easy. */
    TOO_EASY,
    /** This mode is clearly easier than a softer mode listed before it (intervals do not overlap). */
    NOT_MONOTONIC,
    /** The difficulty was asked for but the game's source does not ship it. */
    MISSING_MODE
}
