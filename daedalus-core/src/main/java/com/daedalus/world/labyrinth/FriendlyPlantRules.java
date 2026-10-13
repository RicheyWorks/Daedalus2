// SPDX-License-Identifier: MIT
package com.daedalus.world.labyrinth;

/** Labyrinth helper policy. Host supplies trusted target disposition and threat state. */
public final class FriendlyPlantRules {
    private FriendlyPlantRules() {}
    public enum Target { PLAYER, ALLY, HOSTILE, NEUTRAL, UNKNOWN }
    public enum Action { GUIDE, OFFER_AID, DEFEND, NONE }
    public static Action choose(Target target, boolean threatensPlayer, boolean injured, boolean lost) {
        if (target==null) throw new IllegalArgumentException("target disposition required");
        if (target==Target.HOSTILE) return threatensPlayer?Action.DEFEND:Action.NONE;
        if (target==Target.PLAYER || target==Target.ALLY) {
            if (injured) return Action.OFFER_AID;
            if (lost) return Action.GUIDE;
        }
        return Action.NONE;
    }
}
