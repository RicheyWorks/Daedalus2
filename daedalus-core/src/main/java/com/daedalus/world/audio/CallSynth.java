package com.daedalus.world.audio;

/** Genome -> creature call. Pure function of (species, genome): same animal, same voice, on every engine. */
public final class CallSynth {
    /** Gene slots used, documented for the C++/JS ports. */
    public static final int G_PITCH = 0;
    /** Pitch glide gene. */
    public static final int G_SWEEP = 1;
    /** Overtone count gene. */
    public static final int G_HARM = 2;
    /** Brightness gene. */
    public static final int G_BRIGHT = 3;
    /** Syllable count gene. */
    public static final int G_PULSES = 4;
    /** Syllable length gene. */
    public static final int G_PULSE_LEN = 5;
    /** Gap gene. */
    public static final int G_GAP = 6;
    /** Vibrato gene. */
    public static final int G_VIB = 7;
    /** Breath gene. */
    public static final int G_BREATH = 8;

    private CallSynth() {
    }

    /** Maps a genome to call parameters inside the species' range (log-scale pitch). */
    public static CallSpec design(Species s, Genome g) {
        double hz = s.lowHz() * Math.pow(s.highHz() / s.lowHz(), g.gene(G_PITCH));
        double sweep = round3((g.gene(G_SWEEP) - 0.5) * (s == Species.SONGBIRD ? 2.0 : 0.8));
        int harm = 1 + (int) Math.floor(g.gene(G_HARM) * 7.999);
        double bright = round3(g.gene(G_BRIGHT));
        int pulses = 1 + (int) Math.floor(g.gene(G_PULSES) * (s == Species.SONGBIRD ? 7.999 : 3.999));
        double big = 1.0 - Math.log(hz / 60.0) / Math.log(6000.0 / 60.0);
        int pulseMs = (int) Math.round(60 + 500 * big * (0.5 + g.gene(G_PULSE_LEN)));
        int gapMs = pulses == 1 ? 0 : (int) Math.round(30 + 200 * g.gene(G_GAP));
        double vib = g.gene(G_VIB);
        double breath = round3(Math.min(1.0, g.gene(G_BREATH) * (s == Species.SONGBIRD ? 0.3 : 0.8)));
        return new CallSpec(round3(hz), sweep, harm, bright, pulses, pulseMs, gapMs, round3(3 + 9 * vib),
                round3(vib * 0.8), breath);
    }

    /**
     * Ear-safe view of a call: the fundamental drops by whole octaves until it is under
     * {@link EarRule#MAX_FUNDAMENTAL_HZ}; every other field is kept, so the call keeps its shape and pitch class.
     * Additive only: {@link #design} and the PCS 1 line it produces are unchanged.
     */
    public static CallSpec earSafe(CallSpec c) {
        double hz = c.baseHz();
        while (!EarRule.ok(hz)) {
            hz = round3(hz / 2);
        }
        hz = EarRule.check(hz, "creature call");
        if (hz == c.baseHz()) {
            return c;
        }
        return new CallSpec(hz, c.sweep(), c.harmonics(), c.brightness(), c.pulses(), c.pulseMs(), c.gapMs(),
                c.vibratoHz(), c.vibratoDepth(), c.breath());
    }

    /** {@link #design} followed by {@link #earSafe}: what the game should actually play. */
    public static CallSpec designEarSafe(Species s, Genome g) {
        return earSafe(design(s, g));
    }

    /** Renders 16-bit mono PCM; noise is seeded from the genome, so output is reproducible. */
    public static short[] render(CallSpec c, int sampleRate, long noiseSeed) {
        if (sampleRate < 8000) {
            throw new IllegalArgumentException("sampleRate too low");
        }
        int pulseN = c.pulseMs() * sampleRate / 1000;
        int gapN = c.gapMs() * sampleRate / 1000;
        int total = c.pulses() * pulseN + (c.pulses() - 1) * gapN;
        short[] out = new short[total];
        Rng rng = new Rng(noiseSeed);
        double nyquist = sampleRate / 2.0;
        int pos = 0;
        for (int p = 0; p < c.pulses(); p++) {
            double phase = 0;
            for (int i = 0; i < pulseN; i++) {
                double t = (double) i / pulseN;
                double sec = (double) i / sampleRate;
                double f = c.baseHz() * Math.pow(2, c.sweep() * t)
                        * Math.pow(2, c.vibratoDepth() / 12.0 * Math.sin(2 * Math.PI * c.vibratoHz() * sec));
                phase += 2 * Math.PI * f / sampleRate;
                double tone = 0;
                double norm = 0;
                for (int h = 1; h <= c.harmonics(); h++) {
                    if (f * h >= nyquist) {
                        break;
                    }
                    double a = Math.pow(0.15 + 0.8 * c.brightness(), h - 1);
                    tone += a * Math.sin(h * phase);
                    norm += a;
                }
                tone = norm == 0 ? 0 : tone / norm;
                double noise = rng.nextDouble() * 2 - 1;
                double env = Math.sin(Math.PI * t);
                double v = env * ((1 - c.breath()) * tone + c.breath() * noise) * 0.8;
                out[pos + i] = (short) Math.round(Math.max(-1, Math.min(1, v)) * Short.MAX_VALUE);
            }
            pos += pulseN + (p < c.pulses() - 1 ? gapN : 0);
        }
        return out;
    }

    private static double round3(double v) {
        return Math.round(v * 1000.0) / 1000.0;
    }
}
