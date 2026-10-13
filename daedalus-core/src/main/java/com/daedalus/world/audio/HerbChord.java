package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.List;
import java.util.TreeSet;

/**
 * The herb-chord effect system: herbs planted or brewed together sound a chord, and the chord's quality
 * decides the effect. Consonant chords give clean buffs, dissonant ones give wild effects.
 */
public final class HerbChord {
    /** Effects a chord can grant. */
    public enum Effect {
        /** Major triad. */
        HEAL,
        /** Minor triad. */
        CALM,
        /** Suspended. */
        FOCUS,
        /** Diminished. */
        WARD,
        /** Augmented. */
        HASTE,
        /** Single note or fifth (power chord). */
        STEADY,
        /** Anything else (clusters). */
        CHAOS
    }

    /**
     * Result of sounding a set of herbs.
     *
     * @param root root pitch class
     * @param pitchClasses sorted distinct pitch classes
     * @param quality chord name
     * @param effect effect granted
     * @param strength 0..1, mean potency times consonance
     * @param frequencies playable frequencies (root in octave 4, others stacked above)
     */
    public record Result(int root, List<Integer> pitchClasses, String quality, Effect effect, double strength,
            List<Double> frequencies) {
        /** Defensive copies. */
        public Result {
            pitchClasses = List.copyOf(pitchClasses);
            frequencies = List.copyOf(frequencies);
        }

        @Override
        public List<Integer> pitchClasses() {
            return List.copyOf(pitchClasses);
        }

        @Override
        public List<Double> frequencies() {
            return List.copyOf(frequencies);
        }
    }

    private static final String[] NAMES = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};

    private HerbChord() {
    }

    /** Note name of a pitch class. */
    public static String noteName(int pc) {
        return NAMES[Math.floorMod(pc, 12)];
    }

    /** Sounds the herbs. Needs at least one herb. */
    public static Result sound(List<Herb> herbs) {
        if (herbs == null || herbs.isEmpty()) {
            throw new IllegalArgumentException("at least one herb");
        }
        TreeSet<Integer> set = new TreeSet<>();
        double pot = 0;
        for (Herb h : herbs) {
            set.add(h.pitchClass());
            pot += h.potency();
        }
        pot /= herbs.size();
        List<Integer> pcs = List.copyOf(set);
        for (int root : pcs) {
            TreeSet<Integer> iv = new TreeSet<>();
            for (int p : pcs) {
                iv.add(Math.floorMod(p - root, 12));
            }
            String q = classify(iv);
            if (q != null) {
                return result(root, pcs, q, pot);
            }
        }
        return result(pcs.get(0), pcs, "cluster", pot);
    }

    private static String classify(TreeSet<Integer> iv) {
        String k = iv.toString();
        return switch (k) {
            case "[0]" -> "unison";
            case "[0, 7]" -> "fifth";
            case "[0, 4, 7]" -> "major";
            case "[0, 3, 7]" -> "minor";
            case "[0, 2, 7]", "[0, 5, 7]" -> "sus";
            case "[0, 3, 6]" -> "dim";
            case "[0, 4, 8]" -> "aug";
            case "[0, 4, 7, 11]" -> "maj7";
            case "[0, 3, 7, 10]" -> "min7";
            case "[0, 4, 7, 10]" -> "dom7";
            default -> null;
        };
    }

    private static Result result(int root, List<Integer> pcs, String q, double potency) {
        Effect e;
        double consonance;
        switch (q) {
            case "unison", "fifth" -> {
                e = Effect.STEADY;
                consonance = 1.0;
            }
            case "major", "maj7" -> {
                e = Effect.HEAL;
                consonance = q.equals("major") ? 1.0 : 0.85;
            }
            case "minor", "min7" -> {
                e = Effect.CALM;
                consonance = q.equals("minor") ? 0.95 : 0.8;
            }
            case "sus" -> {
                e = Effect.FOCUS;
                consonance = 0.8;
            }
            case "dim" -> {
                e = Effect.WARD;
                consonance = 0.6;
            }
            case "aug", "dom7" -> {
                e = Effect.HASTE;
                consonance = 0.65;
            }
            default -> {
                e = Effect.CHAOS;
                consonance = 0.4;
            }
        }
        List<Double> freqs = new ArrayList<>();
        for (int p : pcs) {
            int semis = Math.floorMod(p - root, 12) + root - 9;
            freqs.add(Math.round(440.0 * Math.pow(2, semis / 12.0) * 1000.0) / 1000.0);
        }
        freqs.sort(Double::compare);
        double strength = Math.round(potency * consonance * 1000.0) / 1000.0;
        return new Result(root, pcs, q, e, strength, List.copyOf(freqs));
    }
}
