package com.daedalus.world.audio;

import java.util.Locale;

/**
 * Engine-neutral description of one creature call. Unreal (MetaSound/procedural wave), Blender previews
 * and the web player all render from this, so the line format below is the contract ("PCS 1").
 *
 * @param baseHz fundamental frequency
 * @param sweep pitch glide over one pulse, in octaves (negative = falling)
 * @param harmonics number of overtones (1 = pure tone)
 * @param brightness overtone rolloff 0..1 (1 = bright)
 * @param pulses syllables per call
 * @param pulseMs length of one syllable
 * @param gapMs silence between syllables
 * @param vibratoHz vibrato rate
 * @param vibratoDepth vibrato depth in semitones
 * @param breath noise mix 0..1
 */
public record CallSpec(double baseHz, double sweep, int harmonics, double brightness, int pulses,
        int pulseMs, int gapMs, double vibratoHz, double vibratoDepth, double breath) {

    /** Validates ranges. */
    public CallSpec {
        if (!(baseHz > 0) || harmonics < 1 || pulses < 1 || pulseMs < 1 || gapMs < 0) {
            throw new IllegalArgumentException("invalid call spec");
        }
    }

    /** Total call length in milliseconds. */
    public int durationMs() {
        return pulses * pulseMs + (pulses - 1) * gapMs;
    }

    /** Contract line, fixed 3-decimal formatting so ports can compare byte for byte. */
    public String toLine() {
        return String.format(Locale.ROOT, "PCS 1 hz=%.3f sweep=%.3f harm=%d bright=%.3f pulses=%d pulse_ms=%d gap_ms=%d"
                + " vib_hz=%.3f vib_st=%.3f breath=%.3f", baseHz, sweep, harmonics, brightness, pulses, pulseMs, gapMs,
                vibratoHz, vibratoDepth, breath);
    }

    /** Parses a {@link #toLine()} string. */
    public static CallSpec parse(String line) {
        String[] t = line.strip().split(" ");
        if (t.length != 12 || !"PCS".equals(t[0]) || !"1".equals(t[1])) {
            throw new IllegalArgumentException("not a PCS 1 line");
        }
        double[] v = new double[10];
        for (int i = 0; i < 10; i++) {
            int eq = t[i + 2].indexOf('=');
            if (eq < 0) {
                throw new IllegalArgumentException("bad field " + t[i + 2]);
            }
            v[i] = Double.parseDouble(t[i + 2].substring(eq + 1));
        }
        return new CallSpec(v[0], v[1], (int) v[2], v[3], (int) v[4], (int) v[5], (int) v[6], v[7], v[8], v[9]);
    }
}
