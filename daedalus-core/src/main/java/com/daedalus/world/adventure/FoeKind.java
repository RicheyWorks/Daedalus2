// SPDX-License-Identifier: MIT

package com.daedalus.world.adventure;

/**
 * The foes of the Shattering (ADR-037): animals blighted by the meteor's dust, each a lesson in high and
 * low, in the spirit of classic side-view sword fighters: hoppers, shield-bearers and armoured knights.
 *
 * <ul>
 *   <li><b>Blight slime</b> — hops at your shins. No guard; one hit. The first thing anyone beats.</li>
 *   <li><b>Shardback</b> — a beetle whose crystal shell covers its head: it guards high, so crouch and
 *       thrust low. Bites high.</li>
 *   <li><b>Dust wisp</b> — drifts at head height: only a standing thrust reaches it. Swoops high.</li>
 *   <li><b>Stone knight</b> — the duel. Its shield moves between high and low; it strikes at the height it
 *       is not guarding. Read the shield, thrust at the other height, and keep your own shield where its
 *       sword is going.</li>
 * </ul>
 *
 * @param life   hits it takes from an Attack 1 sword
 * @param power  half-hearts its hit costs a Life 1 hero
 * @param exp    experience for beating it (a small hopper is worth 2, an armoured knight 50)
 * @param reach  the only height a thrust can hit it at, or null for either
 * @param guard  the height it always guards, or null (the stone knight's guard moves; see {@link #shifting})
 * @param strike the height it attacks at, or null when it strikes where it is not guarding
 */
public enum FoeKind {
    BLIGHT_SLIME("Blight slime", 1, 1, 2, null, null, Height.LOW, false, 1.6),
    SHARDBACK("Shardback", 2, 2, 5, null, Height.HIGH, Height.HIGH, false, 1.4),
    DUST_WISP("Dust wisp", 1, 1, 3, Height.HIGH, null, Height.HIGH, false, 2.4),
    STONE_KNIGHT("Stone knight", 6, 2, 50, null, null, null, true, 1.2);

    private final String title;
    private final int life;
    private final int power;
    private final int exp;
    private final Height reach;
    private final Height guard;
    private final Height strike;
    private final boolean shifting;
    private final double speed;

    FoeKind(String title, int life, int power, int exp, Height reach, Height guard, Height strike, boolean shifting,
            double speed) {
        this.title = title;
        this.life = life;
        this.power = power;
        this.exp = exp;
        this.reach = reach;
        this.guard = guard;
        this.strike = strike;
        this.shifting = shifting;
        this.speed = speed;
    }

    public String title() {
        return title;
    }

    public int life() {
        return life;
    }

    public int power() {
        return power;
    }

    public int exp() {
        return exp;
    }

    public Height reach() {
        return reach;
    }

    public Height guard() {
        return guard;
    }

    public Height strike() {
        return strike;
    }

    /** True for a foe whose shield moves between high and low (the stone knight). */
    public boolean shifting() {
        return shifting;
    }

    /** Cubes a second it closes in at. */
    public double speed() {
        return speed;
    }
}
