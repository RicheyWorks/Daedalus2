// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.story;

import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.MelodyBrew;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.SplittableRandom;

/**
 * A seed-song record the arks carried, scratched in the shattering: the needle plays the opening of its found tune,
 * then the groove is gone. The scratch always eats the cadence (the closing notes), one or two of them, and always
 * leaves at least two notes to hear. The record is restored by brewing the whole tune, opening plus the missing
 * cadence, in order (see {@link SeedSongSpring#restore}).
 *
 * @param tune    the found tune pressed on this record
 * @param missing how many closing notes the scratch ate (1 or 2)
 */
public record ScratchedRecord(FoundTune tune, int missing) {
    public ScratchedRecord {
        if (tune == null || tune.herbs().size() < MelodyBrew.MIN_HERBS) {
            throw new IllegalArgumentException("a record needs a found tune of at least " + MelodyBrew.MIN_HERBS + " herbs");
        }
        if (missing < 1 || tune.herbs().size() - missing < 2) {
            throw new IllegalArgumentException("scratch must eat 1+ notes and leave 2+: " + tune.name());
        }
    }

    /** Seeded scratch for one record: 1 or 2 closing notes missing, never fewer than 2 heard. */
    public static ScratchedRecord of(FoundTune tune, long seed) {
        int max = Math.min(2, tune.herbs().size() - 2);
        int missing = 1 + new SplittableRandom(seed ^ tune.name().hashCode()).nextInt(max);
        return new ScratchedRecord(tune, missing);
    }

    /** The record item (the tune's LearnedFrom), e.g. {@code Item_YTM_Record_Alpine}. */
    public String item() {
        return tune.learnedFrom();
    }

    /** Herbs the needle still plays, in order. */
    public List<String> heard() {
        return tune.herbs().subList(0, tune.herbs().size() - missing);
    }

    /** Pitch classes still heard, in order. */
    public List<Integer> heardNotes() {
        return tune.notes().subList(0, tune.notes().size() - missing);
    }

    /** True when the tune ends on the note it began with ("it wants to come home"), the Keeper's main hint. */
    public boolean comesHome() {
        List<Integer> n = tune.notes();
        return n.get(0).equals(n.get(n.size() - 1));
    }

    /** True when this kettle order is the whole tune: the heard opening plus the missing cadence. */
    public boolean restoredBy(List<MelodyBrew.Ingredient> items) {
        if (items == null || items.size() != tune.herbs().size()) {
            return false;
        }
        List<String> got = new ArrayList<>();
        items.forEach(i -> got.add(i.herb().toLowerCase(Locale.ROOT)));
        List<String> want = new ArrayList<>();
        tune.herbs().forEach(h -> want.add(h.toLowerCase(Locale.ROOT)));
        return got.equals(want);
    }
}
