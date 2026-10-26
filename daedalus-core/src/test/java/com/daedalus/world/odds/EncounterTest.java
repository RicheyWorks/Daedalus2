package com.daedalus.world.odds;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.tactics.TacticalOrders;
import com.daedalus.world.tactics.TacticalOrders.Verb;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class EncounterTest {

    static final String DTO = """
            DTO 1
            squad s1 tick 5
            order a ATTACK - 0 0 0 | go
            order b FLANK LEFT 100 0 0 | around
            order c RETREAT - 0 0 0 | fall back
            """;

    static final Combatant HERO = Combatant.basic("hero", 100, 10, 0.9, 1);

    private static Map<String, Combatant> stats() {
        return Map.of("a", Combatant.basic("a", 30, 5, 0.5, 1), "b", Combatant.basic("b", 30, 5, 0.5, 1),
                "c", Combatant.basic("c", 30, 5, 0.5, 1));
    }

    @Test
    void readsTheOrdersContract() {
        var parsed = TacticalOrders.parse(DTO);
        assertTrue(parsed.ok(), parsed.error());
        Encounter e = Encounter.fromOrders(parsed.spec(), stats(), HERO, TargetPolicy.LOWEST_HEALTH, 30);
        assertEquals(3, e.foes().size());
        assertEquals(OrderProfile.of(Verb.ATTACK), e.foes().get(0).profile());
        assertEquals(OrderProfile.of(Verb.FLANK), e.foes().get(1).profile());
        assertTrue(e.foes().get(2).profile().leaves());
        OddsReport r = CombatOddsSimulator.run(e, 1, 500);
        assertTrue(r.meanFoesDowned() <= 2.0);
    }

    @Test
    void customProfilesReplaceTheDefaults() {
        var spec = TacticalOrders.parse(DTO).spec();
        Encounter e = Encounter.fromOrders(spec, stats(), HERO, TargetPolicy.FIRST_LISTED, 30,
                v -> new OrderProfile(true, false, 0, 1, 1));
        assertTrue(e.foes().stream().allMatch(f -> f.profile().attacks() && !f.profile().leaves()));
    }

    @Test
    void aUnitWithoutStatsIsAnErrorNotADefault() {
        var spec = TacticalOrders.parse(DTO).spec();
        var ex = assertThrows(IllegalArgumentException.class,
                () -> Encounter.fromOrders(spec, Map.of("a", Combatant.basic("a", 1, 1, 1, 1)), HERO, TargetPolicy.FIRST_LISTED, 30));
        assertTrue(ex.getMessage().contains("b"));
    }

    @Test
    void validation() {
        var f = List.of(Encounter.Foe.fighting(Combatant.basic("f", 1, 1, 1, 1)));
        assertThrows(IllegalArgumentException.class, () -> new Encounter(HERO, List.of(), TargetPolicy.FIRST_LISTED, 10));
        assertThrows(IllegalArgumentException.class, () -> new Encounter(HERO, f, TargetPolicy.FIRST_LISTED, 0));
        assertThrows(IllegalArgumentException.class, () -> new Encounter(HERO, f, TargetPolicy.FIRST_LISTED, Double.NaN));
        assertThrows(IllegalArgumentException.class, () -> new Encounter(HERO, f, TargetPolicy.FIRST_LISTED, 4000));
        assertThrows(NullPointerException.class, () -> new Encounter(null, f, TargetPolicy.FIRST_LISTED, 10));
        assertThrows(NullPointerException.class, () -> new Encounter(HERO, f, null, 10));
        assertThrows(NullPointerException.class, () -> new Encounter.Foe(null, OrderProfile.fighting()));
        var big = new java.util.ArrayList<Encounter.Foe>();
        for (int i = 0; i <= Encounter.MAX_FOES; i++) {
            big.add(f.get(0));
        }
        assertThrows(IllegalArgumentException.class, () -> new Encounter(HERO, big, TargetPolicy.FIRST_LISTED, 10));
        assertThrows(NullPointerException.class,
                () -> Encounter.fromOrders(TacticalOrders.parse(DTO).spec(), stats(), HERO, TargetPolicy.FIRST_LISTED, 10, v -> null));
    }

    @Test
    void foesAreCopiedSoTheSpecIsImmutable() {
        var mutable = new java.util.ArrayList<>(List.of(Encounter.Foe.fighting(Combatant.basic("f", 1, 1, 1, 1))));
        Encounter e = new Encounter(HERO, mutable, TargetPolicy.FIRST_LISTED, 10);
        mutable.clear();
        assertEquals(1, e.foes().size());
    }
}