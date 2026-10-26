// SPDX-License-Identifier: MIT

package com.daedalus.world.brew;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * Melody Brewing (youtube-master, Youtube Master Island): the ORDER herbs go into the kettle is a tune, and the
 * tune's contour decides the tonic. Java port of {@code engines/unreal/ytm-island/herbcombo.py#brew}, same results
 * ({@code MelodyBrewParityTest}). Distinct from prometheus's HerbChord, which reads the same herbs as an unordered chord.
 *
 * <p>Rules: 3 to 5 herbs. Each step is the shortest signed interval (-5..+6) between successive notes. All up = Rise
 * (haste), all down = Fall (cure sickness), up then down = Arch (regen health), down then up = Valley (restore
 * hunger), more turns = Dance (stamina). All steps within 2 semitones doubles the duration; any leap of 5 or more
 * doubles the magnitude. Ending on the first note (a CADENCE) also purifies water. A repeated note, an unknown herb
 * or the wrong count is Noise (mild poison). Tier = average growth stage (1..4), rounded half-to-even like Python.
 */
public final class MelodyBrew {
    public static final int MIN_HERBS = 3;
    public static final int MAX_HERBS = 5;
    public static final String NOISE_TONIC = "Item_YTM_Tonic_Dim_T1";

    /** Contour -> (chord quality used in the tonic id, effect). */
    public static final Map<String, String[]> CONTOUR = Map.of(
            "Rise", new String[] {"Aug", "haste"}, "Fall", new String[] {"Dim", "cure_sickness"},
            "Arch", new String[] {"Major", "regen_health"}, "Valley", new String[] {"Minor", "restore_hunger"},
            "Dance", new String[] {"Sus", "stamina_boost"});

    private MelodyBrew() {
    }

    /** One herb dropped into the kettle, with its growth stage (1 seedling .. 4 bloom). */
    public record Ingredient(String herb, int stage) {
        public Ingredient {
            Objects.requireNonNull(herb, "herb");
        }
    }

    /**
     * The brewed tonic. {@code melody} is the contour name, plus " Cadence" when it purifies water, or "Noise".
     * {@code why} explains a Noise result (empty otherwise).
     */
    public record Tonic(String tonic, String melody, String effect, boolean purifiesWater, int tier, int magnitude,
            int durationS, List<Integer> notes, List<Integer> steps, String why) {
        public Tonic {
            notes = List.copyOf(notes);
            steps = List.copyOf(steps);
        }

        public boolean noise() {
            return melody.equals("Noise");
        }
    }

    /** Shortest signed step between pitch classes, in -5..+6 (herbcombo.step). */
    public static int step(int a, int b) {
        int d = Math.floorMod(b - a, 12);
        return d > 6 ? d - 12 : d;
    }

    public static Tonic brew(List<Ingredient> items) {
        return brew(items, PitchTable.ISLAND_CANON);
    }

    public static Tonic brew(List<Ingredient> items, PitchTable table) {
        if (items == null || items.size() < MIN_HERBS || items.size() > MAX_HERBS) {
            return noise(1, List.of(), List.of(), "use 3-5 herbs");
        }
        List<Integer> notes = new ArrayList<>();
        int stageSum = 0;
        for (Ingredient it : items) {
            var pc = table.pitchOf(it.herb());
            if (pc.isEmpty()) {
                return noise(1, notes, List.of(), "unknown herb " + it.herb());
            }
            notes.add(pc.get());
            stageSum += it.stage();
        }
        List<Integer> steps = new ArrayList<>();
        for (int i = 1; i < notes.size(); i++) {
            steps.add(step(notes.get(i - 1), notes.get(i)));
        }
        int tier = (int) Math.max(1, Math.min(4, Math.rint((double) stageSum / items.size())));
        if (steps.contains(0)) {
            return noise(1, notes, List.of(), "the same note twice in a row");
        }
        int turns = 0;
        for (int i = 1; i < steps.size(); i++) {
            if (Integer.signum(steps.get(i)) != Integer.signum(steps.get(i - 1))) {
                turns++;
            }
        }
        boolean up = steps.get(0) > 0;
        String c = turns == 0 ? (up ? "Rise" : "Fall") : turns == 1 ? (up ? "Arch" : "Valley") : "Dance";
        boolean cadence = notes.get(notes.size() - 1).equals(notes.get(0));
        String[] q = CONTOUR.get(c);
        boolean leap = steps.stream().anyMatch(s -> Math.abs(s) >= 5);
        boolean stepwise = steps.stream().allMatch(s -> Math.abs(s) <= 2);
        int mag = 5 * tier * notes.size() * (leap ? 2 : 1);
        int dur = 60 * tier * (stepwise ? 2 : 1);
        return new Tonic("Item_YTM_Tonic_" + (cadence ? "Seventh" : q[0]) + "_T" + tier, c + (cadence ? " Cadence" : ""),
                q[1], cadence, tier, mag, dur, notes, steps, "");
    }

    private static Tonic noise(int tier, List<Integer> notes, List<Integer> steps, String why) {
        return new Tonic(NOISE_TONIC, "Noise", "poison_mild", false, tier, 0, 0, notes, steps, why);
    }
}
