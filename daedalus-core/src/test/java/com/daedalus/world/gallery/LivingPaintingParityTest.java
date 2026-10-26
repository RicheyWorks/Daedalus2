// SPDX-License-Identifier: MIT

package com.daedalus.world.gallery;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * C++ = Java, line for line (G13 native binding): engines/unreal/core-test/living_painting_parity.txt is written by
 * living_painting_core_test.cpp --write from DaedalusLivingPaintingCore.h. Here the same lines come from the real
 * {@link LivingPainting}, {@link PigmentPalette} and {@link ColourKnowledge}.
 */
class LivingPaintingParityTest {

    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "living_painting_parity.txt");
    private static final String LETTERS = "RYBOGV";

    static ColourKnowledge prism() {
        ColourKnowledge k = new ColourKnowledge();
        for (int i = 0; i < ColourKnowledge.KNOW_AT; i++) {
            k.learn(Pigment.RED);
            k.learn(Pigment.YELLOW);
            k.learn(Pigment.BLUE);
        }
        return k;
    }

    static String mural(int s) {
        long seed = s == 0 ? 0 : (s == 1 ? 999_999_999L : (s * 104_729L * 7_919L + 13) % 1_000_000_000L);
        int w = 1 + s % 12;
        int h = 1 + (s * 5) % 12;
        LivingPainting p = new LivingPainting(seed, w, h);
        ColourKnowledge k = prism();
        StringBuilder cells = new StringBuilder();
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                cells.append(LETTERS.charAt(p.reveal(x, y, k).ordinal()));
            }
        }
        List<String> colours = new ArrayList<>();
        for (Pigment c : p.colours()) {
            colours.add(c.name());
        }
        return "mural s=" + s + " seed=" + seed + " w=" + w + " h=" + h + " subject=" + p.subject() + " colours="
                + String.join(",", colours) + " cells=" + cells;
    }

    static void session(int s, List<String> out) {
        long seed = (s * 15_485_863L + 101) % 1_000_000_000L;
        int w = 2 + s % 3;
        int h = 2 + s % 2;
        LivingPainting p = new LivingPainting(seed, w, h);
        PigmentPalette pal = new PigmentPalette();
        ColourKnowledge k = new ColourKnowledge();
        String[] ing = {"beet", "dawnleaf", "cobalt", "copper", "orange", "salt"};
        List<String> g = new ArrayList<>();
        for (int i = 0; i < 6 + 3 * s; i++) {
            g.add(pal.grind(ing[i % 6]).name());
        }
        out.add("grind s=" + s + " seed=" + seed + " results=" + String.join(",", g));
        out.add("mix s=" + s + " VIOLET -> " + pal.mix(Pigment.VIOLET, k).name());
        for (int i = 0; i < w * h; i++) {
            int x = i % w;
            int y = i / w;
            Pigment pg = Pigment.values()[(int) ((i + seed % 6) % 6)];
            LivingPainting.Result r = p.paint(x, y, pg, pal, k);
            out.add("paint s=" + s + " " + x + " " + y + " " + pg.name() + " -> " + r.name() + " st=" + p.state().name()
                    + " pm=" + p.progressPm() + " smudges=" + p.smudges());
            if (r == LivingPainting.Result.SMUDGED) {
                LivingPainting.Result wr = p.wash(x, y);
                out.add("wash s=" + s + " " + x + " " + y + " -> " + wr.name() + " again=" + p.wash(x, y).name());
            }
        }
        List<String> units = new ArrayList<>();
        List<String> strokes = new ArrayList<>();
        for (Pigment c : Pigment.values()) {
            units.add(String.valueOf(pal.count(c)));
            strokes.add(String.valueOf(k.strokes(c)));
        }
        List<String> abilities = new ArrayList<>();
        for (ColourKnowledge.Ability a : k.abilities()) {
            abilities.add(a.name());
        }
        String reveal = k.abilities().contains(ColourKnowledge.Ability.PRISM_SIGHT) ? p.reveal(0, 0, k).name() : "refused";
        out.add("end s=" + s + " units=" + String.join(",", units) + " strokes=" + String.join(",", strokes) + " abilities="
                + String.join(",", abilities) + " reveal=" + reveal + " st=" + p.state().name());
    }

    static List<String> lines() {
        List<String> out = new ArrayList<>();
        for (int s = 0; s < 24; s++) {
            out.add(mural(s));
        }
        for (int s = 0; s < 6; s++) {
            session(s, out);
        }
        return out;
    }

    @Test
    void cppParityFileMatchesJava() throws Exception {
        List<String> cpp = Files.readAllLines(PARITY, StandardCharsets.UTF_8);
        assertThat(cpp).hasSize(119);
        assertThat(lines()).containsExactlyElementsOf(cpp);
    }
}