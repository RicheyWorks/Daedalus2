// SPDX-License-Identifier: MIT

package com.daedalus.world.odds;

import com.daedalus.world.tactics.TacticalOrders.Verb;

/**
 * What a DTO 1 order verb does to a unit in the odds model. {@code attacks}: the unit fires on the player.
 * {@code leaves}: the unit has left the fight (it can no longer be hit and is not a threat). {@code startDelay}: seconds
 * before the unit joins (flankers and reinforcements arrive late). {@code accuracyMultiplier} scales its hit chance,
 * {@code incomingMultiplier} scales the damage it takes (cover when defending).
 */
public record OrderProfile(boolean attacks, boolean leaves, double startDelay, double accuracyMultiplier,
                           double incomingMultiplier) {

    public OrderProfile {
        if (!Double.isFinite(startDelay) || startDelay < 0 || startDelay > 3600) {
            throw new IllegalArgumentException("startDelay must be 0..3600 seconds");
        }
        if (!Double.isFinite(accuracyMultiplier) || accuracyMultiplier < 0 || accuracyMultiplier > 10) {
            throw new IllegalArgumentException("accuracyMultiplier must be 0..10");
        }
        if (!Double.isFinite(incomingMultiplier) || incomingMultiplier < 0 || incomingMultiplier > 10) {
            throw new IllegalArgumentException("incomingMultiplier must be 0..10");
        }
    }

    /** The default profile for a verb. These are model assumptions to be tuned from in-game telemetry, not contract. */
    public static OrderProfile of(Verb verb) {
        return switch (verb) {
            case HOLD -> new OrderProfile(false, false, 0, 1.0, 1.0);
            case ATTACK -> new OrderProfile(true, false, 0, 1.0, 1.0);
            case FLANK -> new OrderProfile(true, false, 3.0, 1.15, 1.0);
            case DEFEND -> new OrderProfile(true, false, 0, 0.9, 0.7);
            case RETREAT -> new OrderProfile(false, true, 0, 1.0, 1.0);
            case REINFORCE -> new OrderProfile(true, false, 6.0, 1.0, 1.0);
            default -> throw new IllegalArgumentException("unknown verb " + verb);
        };
    }

    /** A unit that simply fights from the start, the profile used when no orders are given. */
    public static OrderProfile fighting() {
        return of(Verb.ATTACK);
    }
}