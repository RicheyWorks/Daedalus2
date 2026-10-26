// SPDX-License-Identifier: MIT

package com.daedalus.world.adventure;

/**
 * Who wins an exchange (ADR-037). Pure rules; the realm runs them sixty times a second, the server serves them
 * so every client plays the same game, and the tests pin them.
 */
public final class Duel {

    /** What a thrust does: lands, is stopped by a shield ("clank"), or passes where the foe is not. */
    public enum Thrust { HIT, GUARDED, OUT_OF_REACH }

    private Duel() {
    }

    /** The height a foe guards right now: fixed for most, the stone knight's moving shield for it. */
    public static Height guardOf(FoeKind foe, Height knightShield) {
        return foe.shifting() ? knightShield : foe.guard();
    }

    /** The height a foe strikes at right now: fixed for most, wherever the stone knight is not guarding. */
    public static Height strikeOf(FoeKind foe, Height knightShield) {
        return foe.shifting() ? knightShield.other() : foe.strike();
    }

    /** A thrust at {@code at} against {@code foe}, whose shield (if it moves) is at {@code knightShield}. */
    public static Thrust thrust(Height at, FoeKind foe, Height knightShield) {
        if (foe.reach() != null && foe.reach() != at) {
            return Thrust.OUT_OF_REACH;
        }
        return guardOf(foe, knightShield) == at ? Thrust.GUARDED : Thrust.HIT;
    }

    /** True when a hero's shield at {@code shield} stops a strike at {@code strike}. */
    public static boolean blocks(Height shield, Height strike) {
        return shield == strike;
    }
}
