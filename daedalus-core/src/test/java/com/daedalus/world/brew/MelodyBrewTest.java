// SPDX-License-Identifier: MIT

package com.daedalus.world.brew;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.audio.Herb;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class MelodyBrewTest {
    static List<MelodyBrew.Ingredient> k(int stage, String... herbs) {
        List<MelodyBrew.Ingredient> out = new ArrayList<>();
        for (String h : herbs) {
            out.add(new MelodyBrew.Ingredient(h, stage));
        }
        return out;
    }

    @Test
    void orderIsTheRecipe() {
        var up = MelodyBrew.brew(k(2, "Doleaf", "Rebell", "Mimint"));
        var down = MelodyBrew.brew(k(2, "Mimint", "Rebell", "Doleaf"));
        assertEquals("Rise", up.melody());
        assertEquals("haste", up.effect());
        assertEquals("Fall", down.melody());
        assertNotEquals(up.tonic(), down.tonic(), "same herbs, other order, other tonic");
        assertEquals(240, up.durationS(), "stepwise doubles duration");
    }

    @Test
    void cadencePurifiesWaterAndLeapsDoubleMagnitude() {
        var t = MelodyBrew.brew(k(3, "Doleaf", "Mimint", "Doleaf"));
        assertTrue(t.purifiesWater());
        assertEquals("Item_YTM_Tonic_Seventh_T3", t.tonic());
        var leap = MelodyBrew.brew(k(1, "Doleaf", "Fasage", "Tisquill"));
        assertEquals(5 * 1 * 3 * 2, leap.magnitude());
    }

    @Test
    void noiseCases() {
        assertEquals("use 3-5 herbs", MelodyBrew.brew(k(2, "Doleaf", "Rebell")).why());
        assertTrue(MelodyBrew.brew(k(1, "Doleaf", "Doleaf", "Mimint")).noise());
        assertTrue(MelodyBrew.brew(k(2, "Doleaf", "Moonwort", "Mimint")).why().contains("unknown herb"));
        assertTrue(MelodyBrew.brew(null).noise());
        assertEquals(MelodyBrew.NOISE_TONIC, MelodyBrew.brew(k(2, "A", "B", "C", "D", "E", "F")).tonic());
    }

    @Test
    void tierRoundsHalfToEvenLikePython() {
        // stages 2,3 average 2.5 -> Python round() gives 2; 3,4 -> 3.5 -> 4
        var a = MelodyBrew.brew(List.of(new MelodyBrew.Ingredient("Doleaf", 2), new MelodyBrew.Ingredient("Rebell", 3),
                new MelodyBrew.Ingredient("Mimint", 2), new MelodyBrew.Ingredient("Fasage", 3)));
        assertEquals(2, a.tier());
        var b = MelodyBrew.brew(List.of(new MelodyBrew.Ingredient("Doleaf", 3), new MelodyBrew.Ingredient("Rebell", 4),
                new MelodyBrew.Ingredient("Mimint", 3), new MelodyBrew.Ingredient("Fasage", 4)));
        assertEquals(4, b.tier());
    }

    @Test
    void pitchTablesArePluggable() {
        assertEquals(Optional.of(0), PitchTable.ISLAND_CANON.pitchOf("doleaf"));
        assertEquals(Optional.empty(), PitchTable.ISLAND_CANON.pitchOf("mint"));
        assertEquals(Optional.of(new Herb("mint", 1).pitchClass()), PitchTable.HERB_CHORD.pitchOf("mint"));
        assertFalse(PitchTable.HERB_CHORD.pitchOf(" ").isPresent());
        PitchTable both = PitchTable.ISLAND_CANON.orElse(PitchTable.HERB_CHORD);
        assertEquals(Optional.of(11), both.pitchOf("Tisquill"));
        assertTrue(both.pitchOf("yarrow").isPresent());
        assertFalse(MelodyBrew.brew(k(2, "Doleaf", "mint", "Mimint"), both).why().contains("unknown"));
        assertEquals(12, PitchTable.canon().size());
    }

    @Test
    void stepIsShortestSignedInterval() {
        assertEquals(6, MelodyBrew.step(0, 6));
        assertEquals(-5, MelodyBrew.step(0, 7));
        assertEquals(1, MelodyBrew.step(11, 0));
        assertEquals(0, MelodyBrew.step(3, 3));
    }
}
