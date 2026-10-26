package com.daedalus.world.retro;

import java.util.List;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class RetroLandTest {
    @Test void configuredDeedsRoundTripButDefaultGeneratorHasNoOwners() {
        var realm = RetroRealmGenerator.generate(7);
        assertTrue(realm.lands().isEmpty());
        var configured = realm.withLands(List.of(new RetroRealm.Land(9999, "FIELD", 2, 2, 4, 4, "HERO")));
        assertEquals(configured.lands(), RetroCodec.read(RetroCodec.write(configured)).lands());
        assertEquals(RetroItem.Kind.EGG, RetroItem.DRAGON_EGG.kind());
        assertEquals(0, RetroItem.DRAGON_EGG.price());
        assertEquals(RetroItem.DRAGON_EGG, realm.chests().stream()
                .filter(c -> c.at().equals(new RetroRealm.Place("CASTLE", 2, 4))).findFirst().orElseThrow().loot().item());
    }

    @Test void rejectsDuplicateUnknownAndOverflowingPlots() {
        var realm = RetroRealmGenerator.generate(7);
        var land = new RetroRealm.Land(0, "FIELD", 1, 1, 4, 4, "");
        assertThrows(IllegalArgumentException.class, () -> realm.withLands(List.of(land, land)));
        assertThrows(IllegalArgumentException.class,
                () -> realm.withLands(List.of(new RetroRealm.Land(1, "MISSING", 1, 1, 4, 4, ""))));
        assertThrows(IllegalArgumentException.class,
                () -> realm.withLands(List.of(new RetroRealm.Land(1, "FIELD", Integer.MAX_VALUE, 1, 4, 4, ""))));
        assertThrows(IllegalArgumentException.class, () -> new RetroRealm.Land(10000, "FIELD", 1, 1, 4, 4, ""));
        assertThrows(IllegalArgumentException.class, () -> new RetroRealm.Land(0, "FIELD", 1, 1, 0, 4, ""));
    }
}
