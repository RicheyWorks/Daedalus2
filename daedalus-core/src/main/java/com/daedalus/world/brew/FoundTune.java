// SPDX-License-Identifier: MIT

package com.daedalus.world.brew;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * A found tune (Youtube Master Island lore): every seed-song record the arks carried holds a short motif. Play the
 * record at the jukebox to learn it; brew exactly that herb ORDER to get its named tonic and bonus.
 * One row of {@code engines/unreal/ytm-island/found_tunes.csv}.
 */
public record FoundTune(String name, String seedSong, List<String> herbs, List<Integer> notes, String baseMelody,
        String baseEffect, String bonus, String tonic, String learnedFrom) {
    public FoundTune {
        herbs = List.copyOf(herbs);
        notes = List.copyOf(notes);
    }

    /** Parses found_tunes.csv (header line, then Name,SeedSong,Herbs,Notes,BaseMelody,BaseEffect,Bonus,Tonic,LearnedFrom). */
    public static List<FoundTune> parseCsv(String text) {
        List<FoundTune> out = new ArrayList<>();
        String[] lines = text.replace("\r", "").split("\n");
        for (int i = 1; i < lines.length; i++) {
            if (lines[i].isBlank()) {
                continue;
            }
            String[] c = lines[i].split(",", -1);
            if (c.length != 9) {
                throw new IllegalArgumentException("found_tunes.csv line " + (i + 1) + ": expected 9 columns, got " + c.length);
            }
            List<Integer> notes = new ArrayList<>();
            for (String n : c[3].split("\\|")) {
                notes.add(Integer.parseInt(n.strip()));
            }
            out.add(new FoundTune(c[0], c[1], Arrays.asList(c[2].split("\\|")), notes, c[4], c[5], c[6], c[7], c[8]));
        }
        return out;
    }
}
