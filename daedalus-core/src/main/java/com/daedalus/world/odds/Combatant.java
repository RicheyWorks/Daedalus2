// SPDX-License-Identifier: MIT

package com.daedalus.world.odds;

import com.daedalus.world.forge.ForgeGrades;
import java.util.Objects;

/**
 * One fighter's numbers: health, and a weapon that swings every {@code cooldown} seconds, hits with {@code accuracy},
 * crits with {@code critChance} for {@code critMultiplier} times the damage, and is blunted by the target's
 * {@code armor}. Armor is flat per hit, but at least 10% of a hit always lands.
 */
public record Combatant(String name, double health, double damage, double accuracy, double critChance,
                        double critMultiplier, double cooldown, double armor) {

    public static final int MAX_NAME = 64;

    public Combatant {
        Objects.requireNonNull(name, "name");
        if (name.isEmpty() || name.length() > MAX_NAME) {
            throw new IllegalArgumentException("name must be 1.." + MAX_NAME + " characters");
        }
        positive(health, "health");
        nonNegative(damage, "damage");
        unit(accuracy, "accuracy");
        unit(critChance, "critChance");
        if (!Double.isFinite(critMultiplier) || critMultiplier < 1 || critMultiplier > 100) {
            throw new IllegalArgumentException("critMultiplier must be 1..100");
        }
        positive(cooldown, "cooldown");
        nonNegative(armor, "armor");
    }

    /** A plain fighter with no crits and no armor. */
    public static Combatant basic(String name, double health, double damage, double accuracy, double cooldown) {
        return new Combatant(name, health, damage, accuracy, 0, 1, cooldown, 0);
    }

    /** The same fighter under a new name and with {@code newHealth} (a live roster's current health). */
    public Combatant renamedWithHealth(String newName, double newHealth) {
        return new Combatant(newName, newHealth, damage, accuracy, critChance, critMultiplier, cooldown, armor);
    }

    /** Damage that gets through {@code armor} for one hit of {@code raw}. */
    static double afterArmor(double raw, double armor) {
        return Math.max(raw * 0.1, raw - armor);
    }

    /** Expected damage per second against a target with {@code targetArmor}, counting hits and crits. */
    public double expectedDps(double targetArmor) {
        double crit = 1 + critChance * (critMultiplier - 1);
        return accuracy * crit * afterArmor(damage, targetArmor) / cooldown;
    }

    /**
     * This fighter with a forged weapon: damage scales by the grade's damage multiplier and a tighter spread raises
     * accuracy by the inverse of the spread multiplier (both per mille, ForgeGrades DFW 1).
     */
    public Combatant withGrade(ForgeGrades.WeaponGrade grade) {
        Objects.requireNonNull(grade, "grade");
        double acc = Math.min(1.0, accuracy * 1000.0 / Math.max(1, grade.spreadPm()));
        return new Combatant(name, health, damage * grade.damagePm() / 1000.0, acc, critChance, critMultiplier,
                cooldown, armor);
    }

    private static void positive(double v, String what) {
        if (!Double.isFinite(v) || v <= 0 || v > 1.0e9) {
            throw new IllegalArgumentException(what + " must be a finite number above 0");
        }
    }

    private static void nonNegative(double v, String what) {
        if (!Double.isFinite(v) || v < 0 || v > 1.0e9) {
            throw new IllegalArgumentException(what + " must be a finite number of at least 0");
        }
    }

    private static void unit(double v, String what) {
        if (!Double.isFinite(v) || v < 0 || v > 1) {
            throw new IllegalArgumentException(what + " must be in [0, 1]");
        }
    }
}