package com.daedalus.world.inventory;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class InventoryCatalogTest {
    private static final String CATALOG = "DIC 1\nrealm GALLERY-CITY\ntheme gallery\ntab ALL\ntab TOOLS\nslot HAND\n"
            + "item BRUSH TOOLS HAND EQUIP,INSPECT Paint Brush\ndetail BRUSH Paints the wall.\n";

    @Test void parsesOrderedImmutableRealmCatalog() {
        var catalog = InventoryCatalog.parse(CATALOG);
        assertEquals("GALLERY-CITY", catalog.realm());
        assertEquals("gallery", catalog.theme());
        assertEquals("Paint Brush", catalog.items().getFirst().name());
        assertEquals("Paints the wall.", catalog.items().getFirst().detail());
        assertThrows(UnsupportedOperationException.class, () -> catalog.tabs().add("BAD"));
        assertThrows(UnsupportedOperationException.class, () -> catalog.items().getFirst().actions().clear());
    }

    @Test void rejectsInvalidReferencesAndDuplicateDefinitions() {
        for (String text : new String[]{CATALOG.replace("TOOLS HAND", "MISSING HAND"),
                CATALOG.replace("TOOLS HAND", "TOOLS -"), CATALOG + "tab TOOLS\n",
                CATALOG + "detail MISSING Bad\n", CATALOG.replace("DIC 1", "DIC 2")}) {
            assertThrows(IllegalArgumentException.class, () -> InventoryCatalog.parse(text));
        }
    }

    @Test void matchesCppCarriageReturnAndRepeatedSpaceHandling() {
        assertEquals(InventoryCatalog.parse(CATALOG),
                InventoryCatalog.parse(CATALOG.replace(" ", "  ").replace("DIC  1", "DIC 1").replace("\n", "\r\n")));
    }
}
