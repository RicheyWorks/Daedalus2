package com.daedalus.world.odds;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.tactics.TacticalOrders;
import java.util.Map;
import org.junit.jupiter.api.Test;

class RosterStatsTest {

    static final String DTR = "DTR 1\nsession sess1 squad pack tick 9\n"
            + "unit g1 grunt 40 60 0 0 0 1\n"
            + "unit g2 grunt 0 60 10 0 0 0\n"
            + "unit k1 knight 90 90 20 0 0 1\n";

    @Test
    void liveUnitsGetTheirKindsTemplateAtCurrentHealth() {
        var roster = TacticalOrders.parseRoster(DTR);
        Map<String, Combatant> stats = RosterStats.fromRoster(roster, Map.of(
                "grunt", new Combatant("t", 60, 8, 0.5, 0, 1, 1, 0), "knight", new Combatant("t", 90, 12, 0.6, 0, 1, 1.4, 4)));
        assertEquals(2, stats.size());
        assertFalse(stats.containsKey("g2"));          // down: never ordered
        assertEquals(40, stats.get("g1").health());
        assertEquals("g1", stats.get("g1").name());
        assertEquals(12, stats.get("k1").damage());
        assertTrue(stats.get("k1").armor() > 0);
    }

    @Test
    void anUnknownKindIsAnError() {
        var roster = TacticalOrders.parseRoster(DTR);
        assertThrows(IllegalArgumentException.class, () -> RosterStats.fromRoster(roster, Map.of("grunt", Combatant.basic("t", 1, 1, 1, 1))));
        assertThrows(NullPointerException.class, () -> RosterStats.fromRoster(null, Map.of()));
        assertThrows(NullPointerException.class, () -> RosterStats.fromRoster(roster, null));
    }

    @Test
    void rosterToOrdersToOdds() {
        var roster = TacticalOrders.parseRoster(DTR);
        var stats = RosterStats.fromRoster(roster, Map.of(
                "grunt", Combatant.basic("t", 60, 8, 0.5, 1.2), "knight", Combatant.basic("t", 90, 12, 0.6, 1.4)));
        var spec = TacticalOrders.parse("DTO 1\nsquad pack tick 9\norder g1 ATTACK - 0 0 0 | go\norder k1 FLANK RIGHT 5 5 0 | around\n").spec();
        Encounter e = Encounter.fromOrders(spec, stats, Combatant.basic("hero", 100, 15, 0.8, 0.8), TargetPolicy.LOWEST_HEALTH, 60);
        OddsReport r = CombatOddsSimulator.run(e, 3, 1000);
        assertEquals(1000, r.trials());
        assertTrue(r.pWin() > 0 && r.pWin() < 1.0);
    }
}