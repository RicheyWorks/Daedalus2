package com.daedalus.world.odds;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.forge.ForgeGrades;
import org.junit.jupiter.api.Test;

class CombatantTest {

    @Test
    void expectedDpsCountsHitsCritsAndArmor() {
        Combatant c = new Combatant("a", 100, 10, 0.5, 0.2, 3, 2, 0);
        // 0.5 * (1 + 0.2*2) * 10 / 2 = 3.5
        assertEquals(3.5, c.expectedDps(0), 1e-12);
        // armor 4 leaves 6 per hit
        assertEquals(0.5 * 1.4 * 6 / 2, c.expectedDps(4), 1e-12);
    }

    @Test
    void armorNeverBlocksMoreThanNinetyPercent() {
        assertEquals(1.0, Combatant.afterArmor(10, 500), 1e-12);
        assertEquals(7.0, Combatant.afterArmor(10, 3), 1e-12);
    }

    @Test
    void forgeGradeScalesDamageAndAccuracy() {
        Combatant base = Combatant.basic("hero", 100, 10, 0.5, 1);
        var grade = ForgeGrades.grade(ForgeGrades.Weapon.BLASTER, ForgeGrades.Material.STARMETAL, 100); // dmg 1437 spread 900
        Combatant g = base.withGrade(grade);
        assertEquals(14.37, g.damage(), 1e-9);
        assertEquals(0.5 * 1000 / 900.0, g.accuracy(), 1e-12);
        Combatant sure = Combatant.basic("hero", 100, 10, 1.0, 1).withGrade(grade);
        assertEquals(1.0, sure.accuracy(), 0.0);   // clamped
    }

    @Test
    void renamedWithHealthKeepsTheWeapon() {
        Combatant c = new Combatant("t", 100, 9, 0.7, 0.1, 2, 1.5, 2).renamedWithHealth("u1", 33);
        assertEquals("u1", c.name());
        assertEquals(33, c.health());
        assertEquals(9, c.damage());
        assertEquals(2, c.armor());
    }

    @Test
    void validationRefusesNonsense() {
        assertThrows(IllegalArgumentException.class, () -> Combatant.basic("", 1, 1, 1, 1));
        assertThrows(IllegalArgumentException.class, () -> Combatant.basic("x".repeat(65), 1, 1, 1, 1));
        assertThrows(IllegalArgumentException.class, () -> Combatant.basic("a", 0, 1, 1, 1));
        assertThrows(IllegalArgumentException.class, () -> Combatant.basic("a", Double.NaN, 1, 1, 1));
        assertThrows(IllegalArgumentException.class, () -> Combatant.basic("a", 1, -1, 1, 1));
        assertThrows(IllegalArgumentException.class, () -> Combatant.basic("a", 1, 1, 1.5, 1));
        assertThrows(IllegalArgumentException.class, () -> Combatant.basic("a", 1, 1, 1, 0));
        assertThrows(IllegalArgumentException.class, () -> new Combatant("a", 1, 1, 1, 2, 1, 1, 0));
        assertThrows(IllegalArgumentException.class, () -> new Combatant("a", 1, 1, 1, 0, 0.5, 1, 0));
        assertThrows(IllegalArgumentException.class, () -> new Combatant("a", 1, 1, 1, 0, 1, 1, -1));
        assertThrows(NullPointerException.class, () -> Combatant.basic(null, 1, 1, 1, 1));
        assertThrows(NullPointerException.class, () -> Combatant.basic("a", 1, 1, 1, 1).withGrade(null));
    }
}