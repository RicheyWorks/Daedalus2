// SPDX-License-Identifier: MIT
package com.daedalus.world;

import java.util.Comparator;
import java.util.HashSet;
import java.util.List;

/** Immutable geometric bundle of existing lands. Not an ownership or mint authorization. */
public record RealmEstate(String realm, List<PlacedLand> lands) {
    /** Placement is supplied from current persisted state, never recomputed from a deed ID after a tug. */
    public record PlacedLand(int number, RealmLandGrid.Cell cell) {
        public PlacedLand {
            if (number < 0 || number >= RealmLandGrid.COUNT || cell == null)
                throw new IllegalArgumentException("invalid placed land");
        }
    }

    public RealmEstate {
        if (realm == null || !realm.matches("[a-z0-9][a-z0-9-]{0,63}") || lands == null)
            throw new IllegalArgumentException("realm and lands are required");
        if (lands.size() < 4 || lands.size() > 100 || lands.stream().anyMatch(java.util.Objects::isNull))
            throw new IllegalArgumentException("estate requires 4..100 placed lands");
        lands = lands.stream().sorted(Comparator.comparingInt(PlacedLand::number)).toList();
        var numbers = new HashSet<Integer>();
        var cells = new HashSet<RealmLandGrid.Cell>();
        int minX=50, minZ=50, maxX=-49, maxZ=-49;
        int district=lands.getFirst().cell().district();
        for (PlacedLand land : lands) {
            var cell=land.cell();
            if (!numbers.add(land.number()) || !cells.add(cell) || cell.district()!=district)
                throw new IllegalArgumentException("duplicate land, occupied cell or split district");
            minX=Math.min(minX,cell.x()); minZ=Math.min(minZ,cell.z());
            maxX=Math.max(maxX,cell.x()); maxZ=Math.max(maxZ,cell.z());
        }
        int side=maxX-minX+1;
        if (side != maxZ-minZ+1 || side*side != lands.size())
            throw new IllegalArgumentException("estate must fill one square without holes");
    }

    public List<Integer> landNumbers() { return lands.stream().map(PlacedLand::number).toList(); }
    public int district() { return lands.getFirst().cell().district(); }
    public int side() { return (int)Math.sqrt(lands.size()); }
}
