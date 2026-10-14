// SPDX-License-Identifier: MIT
package com.daedalus.server.service;

import com.daedalus.server.web.ResourceNotFoundException;
import com.daedalus.world.land.LandGrid;
import com.daedalus.world.land.RealmLayout;
import com.daedalus.world.land.RealmLayoutStore;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import static org.assertj.core.api.Assertions.*;

class RealmLandServiceTest {
    @TempDir Path temp;

    @Test void districtUsesCurrentCellsAndKeepsIdentityAndExactSeed() throws Exception {
        var e = new RealmLayout.Estate(15, 60, 60, 2, Long.MAX_VALUE);
        new RealmLayoutStore(temp).save(new RealmLayout("WORLD-ZERO", 0,
                Set.of(0, LandGrid.number(69, 69)), List.of(e)), -1);
        var service = new RealmLandService(temp.toString());
        var row = service.district("WORLD-ZERO", 66);
        assertThat(row.schemaVersion()).isEqualTo(1);
        assertThat(row.coordinates()).isEqualTo("east-north-realm-metres");
        assertThat(row.revision()).isZero();
        assertThat(row.lands()).containsExactly(new RealmLandService.Land(15, 60, 60, 2,
                Long.toString(Long.MAX_VALUE), 2560, 2560));
        assertThat(row.reservedCells()).containsExactly(LandGrid.number(69, 69));
        assertThat(service.district("WORLD-ZERO", 55).reservedCells()).containsExactly(0);
        assertThat(service.district("WORLD-ZERO", 55).lands()).isEmpty();
        var source = new ArrayList<>(row.lands());
        var copy = new RealmLandService.District(1, "WORLD-ZERO", 0, 66, 100, 256, row.coordinates(), List.of(), source);
        source.clear();
        assertThat(copy.lands()).hasSize(1);
    }

    @Test void missingDisabledAndInvalidInputsDoNotCreateData() {
        var service = new RealmLandService(temp.toString());
        for (String realm : new String[]{"OCEAN", "world-zero", "../OCEAN", null}) {
            assertThatExceptionOfType(ResourceNotFoundException.class).isThrownBy(() -> service.district(realm, 55));
        }
        assertThatExceptionOfType(ResourceNotFoundException.class)
                .isThrownBy(() -> new RealmLandService(" ").district("OCEAN", 55));
        assertThatIllegalArgumentException().isThrownBy(() -> service.district("OCEAN", -1));
        assertThatIllegalArgumentException().isThrownBy(() -> service.district("OCEAN", 100));
        assertThat(temp.resolve("OCEAN.dlay")).doesNotExist();
    }

    @Test void damagedStoreIsUnavailableWithoutLeakingPaths() throws Exception {
        Files.writeString(temp.resolve("OCEAN.dlay"), "broken");
        assertThatExceptionOfType(ResponseStatusException.class)
                .isThrownBy(() -> new RealmLandService(temp.toString()).district("OCEAN", 0))
                .satisfies(ex -> {
                    assertThat(ex.getStatusCode()).isEqualTo(HttpStatus.SERVICE_UNAVAILABLE);
                    assertThat(ex.getReason()).isEqualTo("Realm layout unavailable");
                });
    }

    @Test void allTenThousandRowsArePartitionedIntoOneHundredBoundedDistricts() throws Exception {
        var rows = new ArrayList<RealmLayout.Estate>();
        for (int n = 0; n < LandGrid.COUNT; n++) {
            var c = LandGrid.cell(n);
            rows.add(new RealmLayout.Estate(n, c.x(), c.y(), 1, n));
        }
        new RealmLayoutStore(temp).save(new RealmLayout("OCEAN", 0, Set.of(), rows), -1);
        var service = new RealmLandService(temp.toString());
        var seen = new java.util.HashSet<Integer>();
        for (int d = 0; d < 100; d++) {
            var response = service.district("OCEAN", d);
            assertThat(response.lands()).hasSize(100);
            for (var land : response.lands()) assertThat(seen.add(land.landNumber())).isTrue();
        }
        assertThat(seen).hasSize(10_000);
    }
}
