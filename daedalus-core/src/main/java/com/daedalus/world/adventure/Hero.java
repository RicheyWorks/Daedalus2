// SPDX-License-Identifier: MIT

package com.daedalus.world.adventure;

/**
 * One adventurer's progress (ADR-037): unspent experience, the three levels, and how many foes they have
 * beaten. Immutable: every change returns a new hero. A hero belongs to a person, not a world; the same hero
 * crosses every gate.
 */
public record Hero(String name, int exp, int attack, int magic, int life, int beaten) {

    public Hero {
        if (exp < 0 || attack < 1 || magic < 1 || life < 1 || beaten < 0) {
            throw new IllegalArgumentException("Bad hero " + name);
        }
    }

    public static Hero fresh(String name) {
        return new Hero(name, 0, 1, 1, 1, 0);
    }

    public int level(HeroRules.Stat stat) {
        return switch (stat) {
            case ATTACK -> attack;
            case MAGIC -> magic;
            case LIFE -> life;
        };
    }

    /** Beat a foe: its experience is added, and the count goes up. */
    public Hero beat(FoeKind foe) {
        return new Hero(name, (int) Math.min(Integer.MAX_VALUE / 2, (long) exp + foe.exp()), attack, magic, life,
                beaten == Integer.MAX_VALUE ? beaten : beaten + 1);
    }

    /** True when there is enough experience to raise {@code stat}. */
    public boolean canRaise(HeroRules.Stat stat) {
        return exp >= HeroRules.cost(stat, level(stat));
    }

    /** Raise {@code stat}; the experience goes back to zero (Zelda II). Unchanged when it cannot be raised. */
    public Hero raise(HeroRules.Stat stat) {
        if (!canRaise(stat)) {
            return this;
        }
        return new Hero(name, 0, attack + (stat == HeroRules.Stat.ATTACK ? 1 : 0),
                magic + (stat == HeroRules.Stat.MAGIC ? 1 : 0), life + (stat == HeroRules.Stat.LIFE ? 1 : 0), beaten);
    }

    /** Fall in battle: unspent experience is lost (Zelda II). Levels stay. */
    public Hero fall() {
        return new Hero(name, 0, attack, magic, life, beaten);
    }
}
