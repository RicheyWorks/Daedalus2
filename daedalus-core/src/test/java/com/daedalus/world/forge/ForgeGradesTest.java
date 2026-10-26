package com.daedalus.world.forge;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.forge.ForgeGrades.Material;
import com.daedalus.world.forge.ForgeGrades.Weapon;
import org.junit.jupiter.api.Test;

class ForgeGradesTest {

    @Test
    void neutralTemperBronzeIsBaseline() {
        var g = ForgeGrades.grade(Weapon.SWORD, Material.BRONZE, 50);
        assertEquals("DFW 1 SWORD BRONZE t=50 tier=STANDARD dmg=1000 heat=1000 spread=1000 dur=160", g.encode());
    }

    @Test
    void masterworkStarmetalBlasterGoldenLine() {
        assertEquals("DFW 1 BLASTER STARMETAL t=100 tier=MASTERWORK dmg=1437 heat=800 spread=900 dur=540",
                ForgeGrades.grade(Weapon.BLASTER, Material.STARMETAL, 100).encode());
    }

    @Test
    void obsidianTradeoffs() {
        assertEquals(1180 + 60, ForgeGrades.grade(Weapon.SWORD, Material.OBSIDIAN, 50).damagePm());
        assertEquals(1100, ForgeGrades.grade(Weapon.BLASTER, Material.OBSIDIAN, 50).heatPm());
    }

    @Test
    void boundedAndMonotonicInTemper() {
        for (Weapon w : Weapon.values()) {
            for (Material m : Material.values()) {
                int prevDmg = -1;
                int prevDur = -1;
                for (int t = 0; t <= 100; t++) {
                    var g = ForgeGrades.grade(w, m, t);
                    assertTrue(g.damagePm() >= prevDmg && g.durability() >= prevDur, g.encode());
                    assertTrue(g.damagePm() > 0 && g.damagePm() <= 1500, g.encode());
                    assertTrue(g.heatPm() >= 800 && g.heatPm() <= 1300, g.encode());
                    assertTrue(g.spreadPm() >= 900 && g.spreadPm() <= 1100, g.encode());
                    assertTrue(g.durability() >= 1, g.encode());
                    prevDmg = g.damagePm();
                    prevDur = g.durability();
                }
            }
        }
    }

    @Test
    void deterministic() {
        assertEquals(ForgeGrades.grade(Weapon.BLASTER, Material.IRON, 73),
                ForgeGrades.grade(Weapon.BLASTER, Material.IRON, 73));
    }

    @Test
    void tiers() {
        assertEquals("BRITTLE", ForgeGrades.tier(0));
        assertEquals("CRUDE", ForgeGrades.tier(20));
        assertEquals("STANDARD", ForgeGrades.tier(50));
        assertEquals("FINE", ForgeGrades.tier(80));
        assertEquals("MASTERWORK", ForgeGrades.tier(95));
    }

    @Test
    void rejectsOutOfRangeTemper() {
        assertThrows(IllegalArgumentException.class, () -> ForgeGrades.grade(Weapon.SWORD, Material.IRON, 101));
        assertThrows(IllegalArgumentException.class, () -> ForgeGrades.grade(Weapon.SWORD, Material.IRON, -1));
    }
}
