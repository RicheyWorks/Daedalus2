// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.supper;

import com.daedalus.world.brew.cellar.RootCellar;
import com.daedalus.world.brew.hunt.RecordHunt;
import com.daedalus.world.brew.stones.ChoirStones;
import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.brew.week.FirstWeek;
import java.util.List;

/** A supper guest: an NPC from an earlier chapter (id matches that chapter's talk target). */
public record Guest(String id, String name) {

    /** Everyone the homestead has met, in the order they were met. */
    public static List<Guest> island() {
        return List.of(
                new Guest(SeedSongSpring.KEEPER, "Keeper Oriel"),
                new Guest(RecordHunt.ARCHIVIST, "Archivist Tamsin"),
                new Guest(ChoirStones.MASON, "Mason Hale"),
                new Guest(FirstWeek.WICK, "Old Wick"),
                new Guest("pell", "Pell the rope-maker"),
                new Guest("ida", "Quarry Ida"),
                new Guest("mora", "Hen-wife Mora"),
                new Guest("dov", "Fisher Dov"),
                new Guest(RootCellar.BRINE, "Aunt Brine"));
    }
}
