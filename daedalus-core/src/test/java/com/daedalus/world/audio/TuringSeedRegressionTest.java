// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.brew.MelodyBrew;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import org.junit.jupiter.api.Test;

/**
 * G502 Turing music engine seeded regression sweep: the same seed must give byte-identical output on every
 * call path (raw, ear-safe and peak-checked creature calls, rendered PCM and WAV, ambience beds, melody brews and
 * the jukebox request URLs), 300 seeds each, regardless of call order, thread or default locale.
 * Tests only; nothing here changes engine output.
 */
class TuringSeedRegressionTest {
    private static final int SEEDS = 300;
    /** Renders are the heavy part; every 10th seed keeps CI light (30 per species and path). */
    private static final int RENDER_EVERY = 10;
    private static final int RATE = 8000;
    /** SHA-256 of 300 seeded melody brews; see {@link #melodyBrewGoldenPin()}. */
    private static final String GOLDEN_BREW = "e83daf666f72758b42bc7862dc937cf4d9e36555ae7b7e29fb60eba962d077e9";

    private enum Path { RAW, EAR_SAFE, EAR_SAFE_PEAK }

    private static CallSpec call(Path p, Species s, long seed) {
        Genome g = CallSynthTest.genome(seed);
        return switch (p) {
            case RAW -> CallSynth.design(s, g);
            case EAR_SAFE -> CallSynth.designEarSafe(s, g);
            case EAR_SAFE_PEAK -> CallSynth.designEarSafePeak(s, g);
        };
    }

    private static MessageDigest sha() {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    private static void put(MessageDigest md, String s) {
        md.update(s.getBytes(StandardCharsets.UTF_8));
        md.update((byte) '\n');
    }

    /** Digest of every PCS line (all seeds) plus every sampled WAV, for one path. */
    static String callDigest(Path p, boolean render) {
        MessageDigest md = sha();
        for (Species s : Species.values()) {
            for (long seed = 0; seed < SEEDS; seed++) {
                CallSpec c = call(p, s, seed);
                put(md, s + " " + seed + " " + c.toLine());
                if (render && seed % RENDER_EVERY == 0) {
                    md.update(Wav.encode(CallSynth.render(c, RATE, CallSynthTest.genome(seed).seed()), RATE));
                }
            }
        }
        return HexFormat.of().formatHex(md.digest());
    }

    static AmbienceState ambience(long seed) {
        Rng r = new Rng(seed);
        Biome b = Biome.values()[(int) Long.remainderUnsigned(r.nextLong(), Biome.values().length)];
        return new AmbienceState(b, r.nextDouble() * 24, r.nextDouble(), r.nextDouble(), r.nextDouble());
    }

    static String ambienceDigest() {
        MessageDigest md = sha();
        for (long seed = 0; seed < SEEDS; seed++) {
            put(md, seed + " " + BiomeAmbience.mix(ambience(seed)));
        }
        return HexFormat.of().formatHex(md.digest());
    }

    static List<MelodyBrew.Ingredient> kettle(long seed) {
        Rng r = new Rng(seed ^ 0x5EEDL);
        int n = 3 + (int) Long.remainderUnsigned(r.nextLong(), 3);
        List<MelodyBrew.Ingredient> out = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            String herb = Herb.CANON.get((int) Long.remainderUnsigned(r.nextLong(), Herb.CANON.size()));
            out.add(new MelodyBrew.Ingredient(herb, 1 + (int) Long.remainderUnsigned(r.nextLong(), 4)));
        }
        return out;
    }

    static String brewDigest() {
        MessageDigest md = sha();
        for (long seed = 0; seed < SEEDS; seed++) {
            put(md, seed + " " + MelodyBrew.brew(kettle(seed)));
        }
        return HexFormat.of().formatHex(md.digest());
    }

    static String urlDigest() {
        MessageDigest md = sha();
        JukeboxClient c = new JukeboxClient("http://jukebox.invalid:8080/", u -> new JukeboxTransport.Response(200, null), 0, 1);
        for (long seed = 0; seed < SEEDS; seed++) {
            Rng r = new Rng(seed);
            Map<String, String> q = new HashMap<>();
            int n = 1 + (int) Long.remainderUnsigned(r.nextLong(), 6);
            for (int i = 0; i < n; i++) {
                q.put("k" + Long.toHexString(r.nextLong()), "v " + r.nextLong() + "&é");
            }
            put(md, c.url("/studio/note", q));
        }
        return HexFormat.of().formatHex(md.digest());
    }

    static String everything() {
        StringBuilder sb = new StringBuilder();
        for (Path p : Path.values()) {
            sb.append(callDigest(p, false)).append(' ');
        }
        return sb.append(ambienceDigest()).append(' ').append(brewDigest()).append(' ').append(urlDigest()).toString();
    }

    @Test
    void everyCallPathIsByteIdenticalRunToRunIncludingRenderedAudio() {
        for (Path p : Path.values()) {
            assertThat(callDigest(p, true)).as(p.toString()).isEqualTo(callDigest(p, true));
        }
    }

    @Test
    void callOrderDoesNotLeakStateBetweenCalls() {
        for (Species s : Species.values()) {
            List<String> forward = new ArrayList<>();
            for (long seed = 0; seed < SEEDS; seed++) {
                forward.add(call(Path.EAR_SAFE_PEAK, s, seed).toLine());
            }
            for (long seed = SEEDS - 1; seed >= 0; seed--) {
                assertThat(call(Path.EAR_SAFE_PEAK, s, seed).toLine()).isEqualTo(forward.get((int) seed));
            }
        }
        CallSpec c = call(Path.RAW, Species.SONGBIRD, 7);
        short[] first = CallSynth.render(c, RATE, 42);
        CallSynth.render(call(Path.RAW, Species.BOVINE, 8), RATE, 99);
        assertThat(CallSynth.render(c, RATE, 42)).isEqualTo(first);
    }

    @Test
    void ambienceBrewAndJukeboxUrlsAreStableRunToRun() {
        assertThat(ambienceDigest()).isEqualTo(ambienceDigest());
        assertThat(brewDigest()).isEqualTo(brewDigest());
        assertThat(urlDigest()).isEqualTo(urlDigest());
    }

    @Test
    void threadsGiveTheSameBytesAsTheMainThread() throws Exception {
        String main = everything();
        ExecutorService pool = Executors.newFixedThreadPool(4);
        try {
            List<Future<String>> fs = new ArrayList<>();
            for (int i = 0; i < 4; i++) {
                fs.add(pool.submit(TuringSeedRegressionTest::everything));
            }
            for (Future<String> f : fs) {
                assertThat(f.get()).isEqualTo(main);
            }
        } finally {
            pool.shutdownNow();
        }
    }

    @Test
    void defaultLocaleDoesNotChangeAnyOutput() {
        Locale saved = Locale.getDefault();
        String root = everything();
        try {
            for (Locale l : List.of(Locale.GERMANY, Locale.forLanguageTag("tr-TR"), Locale.forLanguageTag("ar-EG"),
                    Locale.forLanguageTag("hi-IN-u-nu-deva"))) {
                Locale.setDefault(l);
                assertThat(everything()).as(l.toString()).isEqualTo(root);
            }
        } finally {
            Locale.setDefault(saved);
        }
    }

    /**
     * Golden pin, only for the integer-and-string melody brews: no floating point is involved, so the digest is
     * stable across JVMs, OSes and CPUs. Call, render and ambience digests use Math.pow/sin/cos and are checked
     * run-to-run only, not pinned.
     */
    @Test
    void melodyBrewGoldenPin() {
        assertThat(brewDigest()).isEqualTo(GOLDEN_BREW);
    }
}
