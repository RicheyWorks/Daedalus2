package com.daedalus.world.forge;

import java.util.Locale;
import java.util.Objects;

/**
 * DFW 1: Forge Weapon Grades. A pure function that turns the forge outcome (material + temper score) into
 * weapon modifiers for the hero sword and blaster. Integer per-mille math, so it is deterministic and portable
 * (a C++ port can match it byte for byte). It never changes HeroRules; consumers multiply their base stats.
 */
public final class ForgeGrades {

    /** Weapons in the first combat slice (ADR-042: 0 sword, 1 blaster). */
    public enum Weapon { SWORD, BLASTER }

    /** Forge materials, weakest to strongest; per-mille base damage and durability. */
    public enum Material {
        WOOD(800, 60), STONE(900, 90), COPPER(950, 120), BRONZE(1000, 160), IRON(1050, 200),
        STEEL(1120, 280), OBSIDIAN(1180, 140), STARMETAL(1250, 360);

        final int damagePm;
        final int durability;

        Material(int damagePm, int durability) { this.damagePm = damagePm; this.durability = durability; }
    }

    /** Result sheet. Multipliers are per mille (1000 = unchanged). */
    public record WeaponGrade(Weapon weapon, Material material, int temper, String tier,
                              int damagePm, int heatPm, int spreadPm, int durability) {
        /** DFW 1 single-line encoding, stable for parity tests and the link. */
        public String encode() {
            return String.format(Locale.ROOT, "DFW 1 %s %s t=%d tier=%s dmg=%d heat=%d spread=%d dur=%d",
                    weapon, material, temper, tier, damagePm, heatPm, spreadPm, durability);
        }
    }

    private ForgeGrades() { }

    /** Temper tier label from a 0-100 temper score (Forge Temper quench quality). */
    public static String tier(int temper) {
        check(temper);
        if (temper >= 95) return "MASTERWORK";
        if (temper >= 80) return "FINE";
        if (temper >= 50) return "STANDARD";
        if (temper >= 20) return "CRUDE";
        return "BRITTLE";
    }

    /**
     * Grade a forged weapon. Temper adds up to +15% damage (centred on 50) and up to +50% durability, and
     * well-tempered blasters run cooler with tighter spread. Brittle gear loses durability fast.
     */
    public static WeaponGrade grade(Weapon weapon, Material material, int temper) {
        Objects.requireNonNull(weapon, "weapon");
        Objects.requireNonNull(material, "material");
        check(temper);
        int temperDelta = temper - 50;                                   // -50..+50
        int damage = material.damagePm * (1000 + 3 * temperDelta) / 1000; // +/-15%
        int durability = material.durability * (500 + 10 * temper) / 1000; // 50%..150%
        int heat = 1000;
        int spread = 1000;
        if (weapon == Weapon.BLASTER) {
            heat = 1000 - 4 * temperDelta;          // 1200..800: tempered barrels shed heat
            spread = 1000 - 2 * temperDelta;        // 1100..900
            if (material == Material.OBSIDIAN) heat += 100; // glass barrels hold heat
        } else if (material == Material.OBSIDIAN) {
            damage += 60;                           // obsidian edge: sharp but fragile (low base durability)
        }
        return new WeaponGrade(weapon, material, temper, tier(temper), damage, heat, spread, Math.max(1, durability));
    }

    private static void check(int temper) {
        if (temper < 0 || temper > 100) throw new IllegalArgumentException("temper must be 0..100: " + temper);
    }
}
