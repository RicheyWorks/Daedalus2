// SPDX-License-Identifier: MIT

package com.daedalus.world.odds;

import com.daedalus.world.forge.ForgeGrades;
import com.daedalus.world.tactics.TacticalOrders;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Offline demo: the Director's 3-NPC squad (a flanker, a defender and a grunt) against one player, once with a plain
 * bronze sword and once with a masterwork steel one. {@code java -cp ... com.daedalus.world.odds.CombatOddsDemo [seed] [trials]}.
 */
public final class CombatOddsDemo {

    public static final String SPEC = """
            DTO 1
            squad pack_a tick 120
            order grunt1 ATTACK - 0 0 0 | hold the line
            order grunt2 FLANK RIGHT 900 0 0 | go around
            order guard1 DEFEND - 300 0 0 | cover the objective
            """;

    private CombatOddsDemo() {
    }

    /** The demo's report text, so it can be tested without capturing stdout. */
    public static String run(long seed, int trials) {
        TacticalOrders.ParseResult parsed = TacticalOrders.parse(SPEC);
        if (!parsed.ok()) {
            throw new IllegalStateException(parsed.error());
        }
        Map<String, Combatant> stats = new LinkedHashMap<>();
        stats.put("grunt1", new Combatant("grunt1", 60, 8, 0.55, 0.05, 2, 1.2, 1));
        stats.put("grunt2", new Combatant("grunt2", 60, 8, 0.55, 0.05, 2, 1.2, 1));
        stats.put("guard1", new Combatant("guard1", 110, 6, 0.50, 0.00, 1, 1.5, 3));
        Combatant hero = new Combatant("hero", 120, 14, 0.80, 0.15, 2, 0.8, 1);
        StringBuilder out = new StringBuilder();
        for (var grade : new ForgeGrades.WeaponGrade[] {
                ForgeGrades.grade(ForgeGrades.Weapon.SWORD, ForgeGrades.Material.BRONZE, 50),
                ForgeGrades.grade(ForgeGrades.Weapon.SWORD, ForgeGrades.Material.STEEL, 90)}) {
            Encounter e = Encounter.fromOrders(parsed.spec(), stats, hero.withGrade(grade), TargetPolicy.LOWEST_HEALTH, 60);
            OddsReport r = CombatOddsSimulator.run(e, seed, trials);
            out.append(grade.encode()).append('\n').append(r.encode()).append('\n');
            BalanceLimits.Verdict v = BalanceLimits.FAIR.check(r);
            out.append(v.ok() ? "balance OK" : "balance VIOLATED " + v.violations()).append(' ').append(v.warnings()).append('\n');
        }
        return out.toString();
    }

    public static void main(String[] args) {
        long seed = args.length > 0 ? Long.parseLong(args[0]) : 1L;
        int trials = args.length > 1 ? Integer.parseInt(args[1]) : 20_000;
        System.out.print(run(seed, trials));
    }
}