package com.daedalus.world.odds;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;

class BalanceLimitsTest {

    private static OddsReport report(double pWin, double lo, double hi, double medianTtk, double hpFrac, int wins) {
        Summary ttk = wins == 0 ? Summary.EMPTY : new Summary(wins, medianTtk, 1, 1, 1, medianTtk, medianTtk, medianTtk, medianTtk);
        return new OddsReport(1, 1000, wins, 1000 - wins, 0, pWin, lo, hi, ttk, Summary.EMPTY, Summary.EMPTY, hpFrac, 1, 0, 0, 0);
    }

    @Test
    void inTheBandIsOk() {
        var v = BalanceLimits.FAIR.check(report(0.6, 0.57, 0.63, 20, 0.5, 600));
        assertTrue(v.ok());
        assertTrue(v.violations().isEmpty() && v.warnings().isEmpty());
    }

    @Test
    void certainlyTooHardIsAViolation() {
        var v = BalanceLimits.FAIR.check(report(0.10, 0.08, 0.12, 20, 0.5, 100));
        assertFalse(v.ok());
        assertTrue(v.violations().get(0).startsWith("too hard"), v.violations().toString());
    }

    @Test
    void certainlyTooEasyIsAViolation() {
        var v = BalanceLimits.FAIR.check(report(0.97, 0.95, 0.98, 20, 0.1, 970));
        assertFalse(v.ok());
        assertTrue(v.violations().get(0).startsWith("too easy"));
    }

    @Test
    void anInconclusiveBreachIsOnlyAWarning() {
        var low = BalanceLimits.FAIR.check(report(0.38, 0.30, 0.46, 20, 0.5, 380));
        assertTrue(low.ok());
        assertEquals(1, low.warnings().size());
        var high = BalanceLimits.FAIR.check(report(0.87, 0.80, 0.92, 20, 0.5, 870));
        assertTrue(high.ok());
        assertEquals(1, high.warnings().size());
        assertTrue(high.warnings().get(0).contains("ceiling"));
    }

    @Test
    void slowAndPunishingAreViolations() {
        var v = BalanceLimits.FAIR.check(report(0.6, 0.57, 0.63, 90, 0.95, 600));
        assertFalse(v.ok());
        assertEquals(2, v.violations().size());
        assertTrue(v.violations().get(0).startsWith("too slow"));
        assertTrue(v.violations().get(1).startsWith("too punishing"));
        // no wins at all: the time check is skipped, not divided by nothing
        assertTrue(BalanceLimits.FAIR.check(report(0.0, 0.0, 0.0, 0, 0.1, 0)).violations().stream().noneMatch(s -> s.startsWith("too slow")));
    }

    @Test
    void validationAndImmutability() {
        assertThrows(IllegalArgumentException.class, () -> new BalanceLimits(0.9, 0.1, 10, 1));
        assertThrows(IllegalArgumentException.class, () -> new BalanceLimits(-0.1, 0.5, 10, 1));
        assertThrows(IllegalArgumentException.class, () -> new BalanceLimits(0.1, 1.5, 10, 1));
        assertThrows(IllegalArgumentException.class, () -> new BalanceLimits(0.1, 0.5, 0, 1));
        assertThrows(IllegalArgumentException.class, () -> new BalanceLimits(0.1, 0.5, 10, Double.NaN));
        var bad = new java.util.ArrayList<>(List.of("x"));
        var v = new BalanceLimits.Verdict(false, bad, List.of());
        bad.clear();
        assertEquals(1, v.violations().size());
    }

    @Test
    void realReportsFlowThrough() {
        Encounter e = Encounter.allOut(Combatant.basic("hero", 100, 12, 0.8, 1), List.of(Combatant.basic("f", 60, 6, 0.5, 1.2)),
                TargetPolicy.FIRST_LISTED, 60);
        var v = BalanceLimits.FAIR.check(CombatOddsSimulator.run(e, 1, 5000));
        assertTrue(v.violations().stream().anyMatch(s -> s.startsWith("too easy")), v.toString());
        Encounter hard = Encounter.allOut(Combatant.basic("hero", 20, 5, 0.5, 1), List.of(Combatant.basic("f", 200, 15, 0.9, 0.8)),
                TargetPolicy.FIRST_LISTED, 60);
        assertTrue(BalanceLimits.FAIR.check(CombatOddsSimulator.run(hard, 1, 5000)).violations().get(0).startsWith("too hard"));
    }
}