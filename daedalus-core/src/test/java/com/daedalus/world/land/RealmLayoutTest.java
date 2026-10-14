// SPDX-License-Identifier: MIT
package com.daedalus.world.land;

import org.junit.jupiter.api.Test;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import static org.assertj.core.api.Assertions.*;

class RealmLayoutTest {
    @Test void movesPreserveIdentitySeedAndSizeAndChangeDistrict() {
        var first = RealmLayout.empty("WORLD-ZERO", Set.of(0)).place(52, 52, 2, 123);
        var e = first.estates().getFirst();
        var moved = first.move(e.landNumber(), 60, 60);
        assertThat(moved.revision()).isEqualTo(2);
        assertThat(moved.estates()).containsExactly(new RealmLayout.Estate(e.landNumber(), 60, 60, 2, 123));
        assertThat(moved.district(66)).hasSize(1);
        assertThat(moved.district(55)).isEmpty();
        assertThat(first.estates()).containsExactly(e);
        assertThat(moved.estates().getFirst().landNumber()).isNotEqualTo(LandGrid.estate(60, 60, 2));
    }

    @Test void refusesOverlapHubDistrictSplitsAndDuplicateIdentities() {
        var first = RealmLayout.empty("PORTAL", Set.of(0)).place(52, 52, 2, 1);
        assertThatIllegalArgumentException().isThrownBy(() -> first.place(50, 50, 1, 2));
        assertThatIllegalArgumentException().isThrownBy(() -> first.place(53, 53, 2, 2));
        assertThatIllegalArgumentException().isThrownBy(() -> first.place(49, 49, 2, 2));
        assertThatIllegalArgumentException().isThrownBy(() -> first.place(Integer.MAX_VALUE, 0, 4, 2));
        var e = first.estates().getFirst();
        assertThatIllegalArgumentException().isThrownBy(() -> first.move(e.landNumber(), 50, 50));
        assertThatIllegalArgumentException().isThrownBy(() -> first.move(9999, 60, 60));
        assertThatIllegalArgumentException().isThrownBy(() -> new RealmLayout("PORTAL", 0, Set.of(),
                List.of(e, new RealmLayout.Estate(e.landNumber(), 60, 60, 2, 2))));
        var two = first.place(60, 60, 1, 5);
        assertThatIllegalArgumentException().isThrownBy(() -> two.move(e.landNumber(), 60, 60));
    }

    @Test void immutableInputsCanonicalRealmsAndSortedRows() {
        var reserved = new HashSet<Integer>(); reserved.add(0);
        var rows = new ArrayList<RealmLayout.Estate>();
        rows.add(new RealmLayout.Estate(99, 60, 60, 1, 0));
        rows.add(new RealmLayout.Estate(15, 52, 52, 1, 0));
        var layout = new RealmLayout("BRICKS", 8, reserved, rows);
        reserved.clear(); rows.clear();
        assertThat(layout.reservedCells()).containsExactly(0);
        assertThat(layout.estates()).extracting(RealmLayout.Estate::landNumber).containsExactly(15, 99);
        assertThatExceptionOfType(UnsupportedOperationException.class).isThrownBy(() -> layout.estates().clear());
        for (String realm : RealmLayout.REALMS) assertThat(RealmLayout.empty(realm, Set.of()).realm()).isEqualTo(realm);
        assertThatIllegalArgumentException().isThrownBy(() -> RealmLayout.empty("../OCEAN", Set.of()));
        assertThatIllegalArgumentException().isThrownBy(() -> RealmLayout.empty(null, Set.of()));
        assertThatIllegalArgumentException().isThrownBy(() -> RealmLayout.empty("world-zero", Set.of()));
        assertThatIllegalArgumentException().isThrownBy(() -> RealmLayout.empty("OCEAN", Set.of(-1)));
        assertThatIllegalArgumentException().isThrownBy(() -> new RealmLayout("OCEAN", -1, Set.of(), List.of()));
        assertThatIllegalArgumentException().isThrownBy(() -> layout.district(-1));
        assertThatIllegalArgumentException().isThrownBy(() -> layout.district(100));
        assertThatIllegalArgumentException().isThrownBy(() -> new RealmLayout.Estate(-1, 50, 50, 1, 0));
    }

    @Test void fullGridRemainsBoundedAndRealmsAreIndependent() {
        var rows = new ArrayList<RealmLayout.Estate>();
        for (int n = 0; n < LandGrid.COUNT; n++) {
            var c = LandGrid.cell(n);
            rows.add(new RealmLayout.Estate(n, c.x(), c.y(), 1, n));
        }
        var ocean = new RealmLayout("OCEAN", 0, Set.of(), rows);
        var portal = new RealmLayout("PORTAL", 0, Set.of(), rows);
        assertThat(ocean.estates()).hasSize(10_000);
        assertThat(portal.estates()).isEqualTo(ocean.estates());
        assertThat(ocean.district(0)).hasSize(100);
        rows.add(rows.getFirst());
        assertThatIllegalArgumentException().isThrownBy(() -> new RealmLayout("OCEAN", 0, Set.of(), rows));
    }
}
