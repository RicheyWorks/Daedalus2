// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Locale;

/**
 * Prints the odds of Windmere's pond (Prismheart) by day, by night and in an OddsReaper Island storm, checks them with
 * a seeded run, and prices a two-leg Storm Parlay. {@code java ... FishingDemo [fish.json] [seed] [casts]}.
 */
public final class FishingDemo {

    /** Default table, relative to the repository root. */
    public static final String DEFAULT_TABLE = "data/rpg/prism-fish.json";

    private FishingDemo() {
    }

    /** The demo report for a fish table document. */
    public static String run(String json, long seed, int casts) {
        FishTable table = FishTable.fromJson(json);
        StringBuilder s = new StringBuilder();
        s.append("Fishing odds: ").append(table.realm()).append(", ").append(table.size()).append(" fish, seed ")
                .append(seed).append(System.lineSeparator());
        for (Conditions c : List.of(Conditions.DAY, Conditions.NIGHT, Conditions.STORM)) {
            FishingOdds.Breakdown b = FishingOdds.exact(table, c, AnglerSkill.STEADY);
            FishingOdds.Simulation sim = FishingOdds.simulate(table, c, AnglerSkill.STEADY, seed, casts);
            s.append(FishingOdds.describe(b));
            s.append(String.format(Locale.ROOT, "  simulated %d casts: landed %.1f%% [%.1f%%, %.1f%%], %.2f gold/cast%n",
                    sim.casts(), 100 * sim.landRate(), 100 * sim.low(), 100 * sim.high(), sim.meanValue()));
        }
        List<FishSpecies> fish = table.fish();
        List<String> legs = List.of(fish.get(0).name(), fish.get(fish.size() - 1).name());
        FishingOdds.Parlay p = FishingOdds.parlay(table, Conditions.STORM, AnglerSkill.OLD_HAND, legs);
        s.append(String.format(Locale.ROOT, "Storm Parlay %s: %.4f%%, fair multiplier %.1fx%n", legs,
                100 * p.probability(), p.fairMultiplier()));
        return s.toString();
    }

    /** Runs the demo against {@code args[0]} (default {@value #DEFAULT_TABLE}). */
    public static void main(String[] args) throws IOException {
        print(System.out, args);
    }

    static void print(PrintStream out, String[] args) throws IOException {
        Path path = Path.of(args.length > 0 ? args[0] : DEFAULT_TABLE);
        long seed = args.length > 1 ? Long.parseLong(args[1]) : 7L;
        int casts = args.length > 2 ? Integer.parseInt(args[2]) : 4000;
        out.print(run(Files.readString(path, StandardCharsets.UTF_8), seed, casts));
    }
}
