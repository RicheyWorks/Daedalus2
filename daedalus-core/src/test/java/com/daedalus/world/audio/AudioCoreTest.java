package com.daedalus.world.audio;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class AudioCoreTest {
    private static final Genome G = Genome.ofHex("0x3fa29c1e7b44d0815e6a");

    @Test
    void genomeParsesAndWraps() {
        assertEquals(10, G.length());
        assertEquals(0x3f / 255.0, G.gene(0), 1e-12);
        assertEquals(G.gene(0), G.gene(10), 1e-12);
        assertEquals(G, Genome.ofHex("3FA29C1E7B44D0815E6A"));
        assertThrows(IllegalArgumentException.class, () -> Genome.ofHex("abc"));
        assertThrows(IllegalArgumentException.class, () -> Genome.ofHex("zz"));
        assertThrows(IllegalArgumentException.class, () -> Genome.ofHex(null));
    }

    @Test
    void callIsDeterministicAndInsideSpeciesRange() {
        for (Species s : Species.values()) {
            CallSpec a = CallSynth.design(s, G);
            assertEquals(a, CallSynth.design(s, G));
            assertTrue(a.baseHz() >= s.lowHz() - 1e-6 && a.baseHz() <= s.highHz() + 1e-6, s.name());
            assertTrue(a.harmonics() >= 1 && a.harmonics() <= 8);
        }
        assertNotEquals(CallSynth.design(Species.GOAT, G), CallSynth.design(Species.GOAT, Genome.ofHex("00ff")));
    }

    @Test
    void biggerVoicesAreLower() {
        assertTrue(CallSynth.design(Species.BOVINE, G).baseHz() < CallSynth.design(Species.SONGBIRD, G).baseHz());
    }

    @Test
    void contractLineRoundTrips() {
        CallSpec c = CallSynth.design(Species.FOWL, G);
        String line = c.toLine();
        assertTrue(line.startsWith("PCS 1 hz="));
        assertEquals(c, CallSpec.parse(line));
        assertThrows(IllegalArgumentException.class, () -> CallSpec.parse("PCS 2 hz=1"));
    }

    @Test
    void renderLengthDeterminismAndWav() {
        CallSpec c = CallSynth.design(Species.CANID, G);
        short[] a = CallSynth.render(c, 22050, G.seed());
        assertArrayEquals(a, CallSynth.render(c, 22050, G.seed()));
        int expect = c.pulses() * (c.pulseMs() * 22050 / 1000) + (c.pulses() - 1) * (c.gapMs() * 22050 / 1000);
        assertEquals(expect, a.length);
        int peak = 0;
        for (short s : a) {
            peak = Math.max(peak, Math.abs(s));
        }
        assertTrue(peak > 1000, "audible");
        byte[] w = Wav.encode(a, 22050);
        assertEquals("RIFF", new String(w, 0, 4, StandardCharsets.US_ASCII));
        ByteBuffer b = ByteBuffer.wrap(w).order(ByteOrder.LITTLE_ENDIAN);
        assertEquals(22050, b.getInt(24));
        assertEquals(a.length * 2, b.getInt(40));
        assertThrows(IllegalArgumentException.class, () -> CallSynth.render(c, 100, 1));
    }

    @Test
    void ambienceRespectsHeadroomAndTime() {
        for (Biome b : Biome.values()) {
            for (int h = 0; h < 24; h += 3) {
                List<AmbienceLayer> m = BiomeAmbience.mix(new AmbienceState(b, h, 1, 1, 1));
                double sum = m.stream().mapToDouble(AmbienceLayer::gain).sum();
                assertTrue(sum <= BiomeAmbience.HEADROOM + 0.01, b + "@" + h);
                assertFalse(m.isEmpty());
            }
        }
        List<String> noon = ids(BiomeAmbience.mix(new AmbienceState(Biome.GRASSLAND, 13, 0, 0, 0)));
        List<String> mid = ids(BiomeAmbience.mix(new AmbienceState(Biome.GRASSLAND, 1, 0, 0, 0)));
        assertTrue(noon.contains("insects_day") && !noon.contains("crickets_night"));
        assertTrue(mid.contains("crickets_night") && !mid.contains("insects_day"));
        assertTrue(ids(BiomeAmbience.mix(new AmbienceState(Biome.FOREST, 12, 0, 0, 0.8))).contains("water"));
        assertEquals(BiomeAmbience.mix(new AmbienceState(Biome.COAST, 25, 0, 0.5, 0)),
                BiomeAmbience.mix(new AmbienceState(Biome.COAST, 1, 0, 0.5, 0)));
        assertThrows(IllegalArgumentException.class, () -> new AmbienceState(null, 0, 0, 0, 0));
    }

    @Test
    void rainMufflesBeds() {
        double dry = BiomeAmbience.mix(new AmbienceState(Biome.FOREST, 12, 0, 1, 0)).get(0).lowpassHz();
        double wet = BiomeAmbience.mix(new AmbienceState(Biome.FOREST, 12, 1, 1, 0)).stream()
                .filter(l -> l.id().equals("wind")).findFirst().orElseThrow().lowpassHz();
        assertTrue(wet < dry || dry == 0);
    }

    @Test
    void herbChordFindsQualitiesFromPitchClasses() {
        List<Herb> pool = new ArrayList<>();
        String[] names = {"mint", "sage", "yarrow", "thyme", "rue", "fennel", "basil", "dill", "lovage", "comfrey",
            "tansy", "borage", "chervil", "sorrel", "hyssop", "valerian", "mugwort", "chamomile", "lavender", "rosemary"};
        for (String n : names) {
            pool.add(new Herb(n, 1));
        }
        Herb[] byPc = new Herb[12];
        for (Herb h : pool) {
            byPc[h.pitchClass()] = byPc[h.pitchClass()] == null ? h : byPc[h.pitchClass()];
        }
        int found = 0;
        for (int r = 0; r < 12; r++) {
            Herb a = byPc[r];
            Herb b = byPc[(r + 4) % 12];
            Herb c = byPc[(r + 7) % 12];
            if (a != null && b != null && c != null) {
                HerbChord.Result res = HerbChord.sound(List.of(a, b, c));
                assertEquals("major", res.quality());
                assertEquals(HerbChord.Effect.HEAL, res.effect());
                assertEquals(r, res.root());
                assertEquals(1.0, res.strength(), 1e-9);
                assertEquals(3, res.frequencies().size());
                found++;
            }
        }
        assertTrue(found > 0, "pool covers at least one major triad");
    }

    @Test
    void herbChordSingleAndCluster() {
        HerbChord.Result one = HerbChord.sound(List.of(new Herb("Mint", 0.5), new Herb("mint ", 1)));
        assertEquals("unison", one.quality());
        assertEquals(HerbChord.Effect.STEADY, one.effect());
        assertEquals(0.75, one.strength(), 1e-9);
        assertEquals(new Herb("mint", 0).pitchClass(), one.root());
        assertThrows(IllegalArgumentException.class, () -> HerbChord.sound(List.of()));
        assertThrows(IllegalArgumentException.class, () -> new Herb(" ", 1));
        assertEquals("A", HerbChord.noteName(9));
    }

    @Test
    void herbChordIsOrderIndependent() {
        List<Herb> a = List.of(new Herb("sage", 0.4), new Herb("rue", 0.9), new Herb("dill", 0.2));
        List<Herb> b = List.of(a.get(2), a.get(0), a.get(1));
        assertEquals(HerbChord.sound(a), HerbChord.sound(b));
    }

    private static List<String> ids(List<AmbienceLayer> m) {
        return m.stream().map(AmbienceLayer::id).toList();
    }
}
