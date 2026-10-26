// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.convoy;

/**
 * Loss model for arks crossing the belt in convoys. Within a convoy, a common belt storm strikes the whole convoy with
 * chance {@code shock}; each ark is then lost independently with chance {@code lossCalm} (no storm) or
 * {@code lossStorm} (storm). Sailing together gives mutual aid: each extra ark in a convoy cuts every member's loss
 * chance by {@code aid} (relative), down to at most {@link #MAX_AID_CUT} off. Separate convoys meet separate storms.
 */
public record ConvoyRisk(double shock, double lossCalm, double lossStorm, double aid) {

    /** Mutual aid can cut loss chances by at most this fraction. */
    public static final double MAX_AID_CUT = 0.45;

    /** OddsReaper belt: 30% storm chance per convoy, 10% / 60% loss, 25% aid per extra ark (capped at 45%). */
    public static final ConvoyRisk ODDSREAPER = new ConvoyRisk(0.30, 0.10, 0.60, 0.25);

    public ConvoyRisk {
        if (!inUnit(shock) || !inUnit(lossCalm) || !inUnit(lossStorm) || !inUnit(aid)) {
            throw new IllegalArgumentException("all chances must be in [0, 1]");
        }
    }

    private static boolean inUnit(double x) {
        return x >= 0 && x <= 1;
    }

    /** Fraction cut from loss chances for a convoy of {@code size} arks. */
    public double aidCut(int size) {
        if (size < 1) {
            throw new IllegalArgumentException("size must be >= 1: " + size);
        }
        return Math.min(MAX_AID_CUT, aid * (size - 1));
    }

    /** Per-ark loss chance in a convoy of {@code size}, with or without the storm. */
    public double loss(int size, boolean storm) {
        return (storm ? lossStorm : lossCalm) * (1 - aidCut(size));
    }
}
