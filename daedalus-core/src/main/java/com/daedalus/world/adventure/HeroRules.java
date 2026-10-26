// SPDX-License-Identifier: MIT

package com.daedalus.world.adventure;

/**
 * The numbers of the hero game (ADR-037), in one place for the server and every client.
 *
 * <p><b>Levels are a choice, and they never stop.</b> A hero has three levels, Attack, Magic and Life, each
 * from 1 up, with no ceiling ("some people will want to grind experience; we have no max level"). Experience
 * piles up from every foe beaten; when it reaches the cost of raising any one of them, the hero may choose
 * which, and the experience goes back to zero, by design. The first seven costs of each are
 * from the fixed table (Life cheapest, Attack dearest); past them, each level costs half again the one before.
 *
 * <p><b>What a level does.</b> Attack is the damage of a thrust. Life is hearts: three, and one more per
 * level, and a Life level also blunts a foe's blow. Magic is the size of the magic meter, which pays for
 * Heal. A fall in battle costs all unspent experience, by design.
 */
public final class HeroRules {

    /** Levels whose costs come from the fixed table; beyond {@code TABLE_LEVELS} each costs half again the last. */
    public static final int TABLE_LEVELS = 8;
    /** No level costs more than this, so experience (an int) can always reach it. */
    public static final int COST_CEILING = 1_000_000_000;
    /** The experience costs to reach levels 2..8. */
    private static final int[] ATTACK = {200, 500, 1000, 2000, 3000, 5000, 8000};
    private static final int[] MAGIC = {100, 300, 700, 1200, 2200, 3500, 6000};
    private static final int[] LIFE = {50, 150, 400, 800, 1500, 2500, 4000};
    /** Magic a Heal costs, and the half-hearts it restores. */
    public static final int HEAL_COST = 4;
    public static final int HEAL_AMOUNT = 6;

    public enum Stat { ATTACK, MAGIC, LIFE }

    private HeroRules() {
    }

    /** Experience needed to raise {@code stat} from {@code level}; there is always a next level. */
    public static int cost(Stat stat, int level) {
        if (level < 1) {
            throw new IllegalArgumentException("level " + level);
        }
        int[] table = switch (stat) {
            case ATTACK -> ATTACK;
            case MAGIC -> MAGIC;
            case LIFE -> LIFE;
        };
        if (level < TABLE_LEVELS) {
            return table[level - 1];
        }
        long c = table[table.length - 1];
        for (int l = TABLE_LEVELS; l <= level && c < COST_CEILING; l++) {
            c = c * 3 / 2;
        }
        return (int) Math.min(COST_CEILING, c);
    }

    /** Damage of one thrust at this Attack level, in a foe's life points. */
    public static int damage(int attack) {
        return attack <= 2 ? attack : attack - 1 + attack / 3;
    }

    /** Most half-hearts a hero of this Life level holds: three hearts, and one more per level. */
    public static int maxLife(int life) {
        return 2 * (2 + life);
    }

    /** Half-hearts a foe's blow costs: its power, blunted by one for every two Life levels past the first. */
    public static int hurt(FoeKind foe, int life) {
        return Math.max(1, foe.power() - (life - 1) / 2);
    }

    /** Size of the magic meter at this Magic level. */
    public static int maxMagic(int magic) {
        return 4 + 4 * magic;
    }
}
