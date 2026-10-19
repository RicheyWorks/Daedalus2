package com.daedalus.world.odds;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.odds.CombatOddsSimulator.Outcome;
import com.daedalus.world.tactics.TacticalOrders.Verb;
import java.util.List;
import org.junit.jupiter.api.Test;

class CombatOddsSimulatorTest {

    static Combatant hero(double hp, double dmg, double acc, double cd) {
        return Combatant.basic("hero", hp, dmg, acc, cd);
    }

    static Combatant foe(String name, double hp, double dmg, double acc, double cd) {
        return Combatant.basic(name, hp, dmg, acc, cd);
    }

    static Encounter duel(Combatant p, Combatant f) {
        return Encounter.allOut(p, List.of(f), TargetPolicy.FIRST_LISTED, 600);
    }

    @Test
    void sureKillWinsEveryTimeInTheExpectedWindow() {
        // 25 hp, 10 per sure hit, 1s cooldown: three swings, so 2 <= ttk < 3 (random phase in [0,1)).
        Encounter e = duel(hero(100, 10, 1, 1), foe("f", 25, 5, 0, 1));
        OddsReport r = CombatOddsSimulator.run(e, 1, 500);
        assertEquals(500, r.wins());
        assertEquals(1.0, r.pWin());
        assertEquals(1.0, r.pWinHigh(), 1e-12);
        assertTrue(r.pWinLow() > 0.99);
        assertTrue(r.winTtk().min() >= 2.0 && r.winTtk().max() < 3.0, r.winTtk().toString());
        assertEquals(2.5, r.winTtk().mean(), 0.05);
        assertEquals(0, r.healthLost().mean());
        assertEquals(1.0, r.meanFoesDowned());
        assertEquals(0, r.losses());
        assertEquals(0, r.lossTtd().n());
    }

    @Test
    void sureDeathLosesEveryTime() {
        Encounter e = duel(hero(50, 10, 0, 1), foe("f", 25, 1000, 1, 1));
        OddsReport r = CombatOddsSimulator.run(e, 2, 300);
        assertEquals(300, r.losses());
        assertEquals(0.0, r.pWin());
        assertEquals(0.0, r.pWinLow(), 1e-12);
        assertTrue(r.pWinHigh() < 0.02);
        assertEquals(1.0, r.pLoss());
        assertEquals(50, r.healthLost().mean(), 1e-9);
        assertEquals(1.0, r.meanHealthLostFraction(), 1e-9);
        assertEquals(0, r.winTtk().n());
        assertEquals(300, r.lossTtd().n());
        assertEquals(-1.0, r.expectedValue(), 1e-9);
    }

    @Test
    void stalemateIsADrawAtTheTimeLimit() {
        Encounter e = Encounter.allOut(hero(50, 10, 0, 1), List.of(foe("f", 25, 5, 0, 1)), TargetPolicy.FIRST_LISTED, 30);
        OddsReport r = CombatOddsSimulator.run(e, 3, 100);
        assertEquals(100, r.draws());
        assertEquals(1.0, r.pDraw());
        assertEquals(0.0, r.expectedValue());
        CombatOddsSimulator.Trial t = CombatOddsSimulator.simulateOnce(e, new OddsRng(1));
        assertEquals(Outcome.DRAW, t.outcome());
        assertEquals(30, t.seconds());
    }

    @Test
    void aMirrorDuelIsAboutFiftyFifty() {
        Encounter e = duel(hero(10, 10, 1, 1), foe("f", 10, 10, 1, 1));   // one hit kills, same clock
        OddsReport r = CombatOddsSimulator.run(e, 11, 40_000);
        assertEquals(0.5, r.pWin(), 0.015);
        assertTrue(r.pWinLow() < 0.5 && r.pWinHigh() > 0.5);
        assertEquals(40_000, r.wins() + r.losses());
        assertEquals(0, r.draws());
    }

    @Test
    void theIntervalCoversTheTruthForAKnownRace() {
        // Player swings every 1s, foe every 2s, both one-hit kills, both sure hits. Phases are U[0,1) and U[0,2).
        // Player wins iff its first swing lands before the foe's first swing: P = 1 - E[min(U1, ...)]: the foe's first swing
        // time F ~ U[0,2) beats player's U1 ~ U[0,1) with probability 1 - (1/2)*(1/2)... computed exactly below.
        // P(U1 < F) = E over F: F>=1 -> 1 (prob 1/2); F<1 -> F (uniform on [0,1), mean 1/2): 0.5 + 0.5*0.5 = 0.75.
        Encounter e = duel(hero(10, 10, 1, 1), foe("f", 10, 10, 1, 2));
        OddsReport r = CombatOddsSimulator.run(e, 5, 200_000);
        assertTrue(r.pWinLow() <= 0.75 && 0.75 <= r.pWinHigh(), r.encode());
    }

    @Test
    void sameSeedSameReportAndOtherSeedsDiffer() {
        Encounter e = duel(hero(60, 7, 0.7, 0.9), foe("f", 80, 6, 0.6, 1.1));
        String a = CombatOddsSimulator.run(e, 1234, 3000).encode();
        assertEquals(a, CombatOddsSimulator.run(e, 1234, 3000).encode());
        assertNotEquals(a, CombatOddsSimulator.run(e, 1235, 3000).encode());
        assertTrue(a.startsWith("DOR 1 seed=1234 trials=3000 "), a);
    }

    @Test
    void moreTrialsNarrowTheInterval() {
        Encounter e = duel(hero(60, 7, 0.7, 0.9), foe("f", 80, 6, 0.6, 1.1));
        double narrow = CombatOddsSimulator.run(e, 9, 20_000).pWinWidth();
        double wide = CombatOddsSimulator.run(e, 9, 200).pWinWidth();
        assertTrue(narrow < wide / 4, narrow + " vs " + wide);
    }

    @Test
    void focusFireTakesLessDamageThanListedOrder() {
        Combatant tank = foe("tank", 100, 1, 1, 1);
        Combatant glass = foe("glass", 10, 8, 1, 1);
        Combatant p = hero(1000, 10, 1, 1);
        double listed = CombatOddsSimulator.run(Encounter.allOut(p, List.of(tank, glass), TargetPolicy.FIRST_LISTED, 600), 4, 2000)
                .healthLost().mean();
        double weakest = CombatOddsSimulator.run(Encounter.allOut(p, List.of(tank, glass), TargetPolicy.LOWEST_HEALTH, 600), 4, 2000)
                .healthLost().mean();
        double threat = CombatOddsSimulator.run(Encounter.allOut(p, List.of(tank, glass), TargetPolicy.HIGHEST_THREAT, 600), 4, 2000)
                .healthLost().mean();
        assertTrue(weakest < listed, weakest + " vs " + listed);
        assertTrue(threat < listed, threat + " vs " + listed);
        assertEquals(weakest, threat, 1e-9);   // here the weakest unit is also the biggest threat
    }

    @Test
    void ordersChangeTheOdds() {
        Combatant p = hero(100, 10, 1, 1);
        Combatant f = foe("f", 40, 5, 0.8, 1);
        double attack = loss(p, f, Verb.ATTACK);
        double flank = loss(p, f, Verb.FLANK);        // arrives 3 s late: less time to hurt the player
        assertTrue(flank < attack, flank + " vs " + attack);
        // Defending soaks damage (x0.7), so the kill takes longer and the player bleeds more.
        assertTrue(loss(p, f, Verb.DEFEND) > attack);
        // A reinforcement is later than a flanker.
        assertTrue(loss(p, f, Verb.REINFORCE) < flank);
    }

    private static double loss(Combatant p, Combatant f, Verb v) {
        Encounter e = new Encounter(p, List.of(new Encounter.Foe(f, OrderProfile.of(v))), TargetPolicy.FIRST_LISTED, 600);
        return CombatOddsSimulator.run(e, 6, 3000).healthLost().mean();
    }

    @Test
    void unitsThatHoldOrRetreatAreNotThreats() {
        Combatant p = hero(100, 10, 1, 1);
        Combatant f = foe("f", 40, 50, 1, 1);
        for (Verb v : new Verb[] {Verb.HOLD, Verb.RETREAT}) {
            Encounter e = new Encounter(p, List.of(new Encounter.Foe(f, OrderProfile.of(v))), TargetPolicy.FIRST_LISTED, 60);
            OddsReport r = CombatOddsSimulator.run(e, 1, 50);
            assertEquals(50, r.wins(), v.toString());
            assertEquals(0.0, r.winTtk().max());
            assertEquals(0.0, r.healthLost().mean());
        }
    }

    @Test
    void playerArmorBlunts() {
        Combatant armored = new Combatant("hero", 100, 10, 1, 0, 1, 1, 9);   // 10 -> max(1, 10-9) = 1 per hit
        Encounter plain = duel(hero(100, 10, 1, 1), foe("f", 1000, 10, 1, 1));
        Encounter tough = duel(armored, foe("f", 1000, 10, 1, 1));
        assertTrue(CombatOddsSimulator.run(tough, 1, 200).lossTtd().p50() > 5 * CombatOddsSimulator.run(plain, 1, 200).lossTtd().p50());
    }

    @Test
    void critsRaiseDamageAndWinChance() {
        Combatant noCrit = hero(60, 10, 0.9, 1);
        Combatant crit = new Combatant("hero", 60, 10, 0.9, 0.5, 3, 1, 0);
        Combatant f = foe("f", 120, 6, 0.8, 1);
        assertTrue(CombatOddsSimulator.run(duel(crit, f), 8, 5000).pWin() > CombatOddsSimulator.run(duel(noCrit, f), 8, 5000).pWin());
    }

    @Test
    void expectedValueUsesPayoffsAndHealthCost() {
        Encounter e = duel(hero(100, 10, 1, 1), foe("f", 25, 5, 0.5, 1));
        Payoffs pay = new Payoffs(10, -5, 1, 0.1);
        OddsReport r = CombatOddsSimulator.run(e, 2, 4000, pay);
        double expected = r.pWin() * 10 + r.pLoss() * -5 + r.pDraw() * 1 - 0.1 * r.healthLost().mean();
        assertEquals(expected, r.expectedValue(), 1e-9);
        assertTrue(r.expectedValueLow() < r.expectedValue() && r.expectedValue() < r.expectedValueHigh());
        assertThrows(IllegalArgumentException.class, () -> new Payoffs(1, 1, 1, -1));
        assertThrows(IllegalArgumentException.class, () -> new Payoffs(Double.NaN, 1, 1, 0));
    }

    @Test
    void wilsonIntervalIsTheTextbookOne() {
        double[] zero = CombatOddsSimulator.wilson(0, 100);
        assertEquals(0.0, zero[0], 1e-12);
        assertEquals(0.0370, zero[1], 5e-4);
        double[] all = CombatOddsSimulator.wilson(100, 100);
        assertEquals(1.0, all[1], 1e-12);
        assertEquals(0.9630, all[0], 5e-4);
        double[] half = CombatOddsSimulator.wilson(50, 100);
        assertEquals(0.4038, half[0], 5e-4);
        assertEquals(0.5962, half[1], 5e-4);
    }

    @Test
    void refusesBadRuns() {
        Encounter e = duel(hero(10, 1, 1, 1), foe("f", 10, 1, 1, 1));
        assertThrows(IllegalArgumentException.class, () -> CombatOddsSimulator.run(e, 1, 0));
        assertThrows(IllegalArgumentException.class, () -> CombatOddsSimulator.run(e, 1, CombatOddsSimulator.MAX_TRIALS + 1));
        assertThrows(NullPointerException.class, () -> CombatOddsSimulator.run(null, 1, 10));
        assertThrows(NullPointerException.class, () -> CombatOddsSimulator.run(e, 1, 10, null));
    }

    @Test
    void goldenReportLocksTheModel() {
        Encounter e = Encounter.allOut(new Combatant("hero", 100, 14, 0.8, 0.15, 2, 0.8, 1),
                List.of(new Combatant("a", 90, 12, 0.6, 0.05, 2, 1.0, 1), new Combatant("b", 90, 12, 0.6, 0.05, 2, 1.0, 1)),
                TargetPolicy.LOWEST_HEALTH, 60);
        assertEquals(GOLDEN, CombatOddsSimulator.run(e, 20261018L, 5000).encode());
    }

    static final String GOLDEN = "DOR 1 seed=20261018 trials=5000 win=1340 loss=3660 draw=0 pwin=0.2680 ci95=[0.2559,0.2805]"
            + " ttk{n=1340 mean=10.697 sd=1.406 p50=10.598 p90=12.613 p99=14.412} ttd{n=3660 mean=7.826 sd=2.206 p50=7.636 p90=10.811 p99=13.248}"
            + " hp{n=5000 mean=95.918 sd=9.874 p50=100.000 p90=100.000 p99=100.000} hpfrac=0.9592 downed=1.031 ev=-0.4640 ev95=[-0.4886,-0.4394]";
}