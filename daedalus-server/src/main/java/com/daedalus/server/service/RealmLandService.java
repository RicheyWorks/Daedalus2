// SPDX-License-Identifier: MIT
package com.daedalus.server.service;

import com.daedalus.server.web.ResourceNotFoundException;
import com.daedalus.world.land.LandGrid;
import com.daedalus.world.land.RealmLayout;
import com.daedalus.world.land.RealmLayoutStore;
import java.io.IOException;
import java.nio.file.Path;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

/** Read-only view of operator-provisioned placement data. Does not infer ownership or terrain hosting. */
@Service
public class RealmLandService {
    private final RealmLayoutStore store;

    public record Land(int landNumber, int cellX, int cellY, int size, String seed,
                       double originEastMetres, double originNorthMetres) { }
    public record District(int schemaVersion, String realm, long revision, int district,
                           int gridSide, double pitchMetres, String coordinates,
                           List<Integer> reservedCells, List<Land> lands) {
        public District {
            reservedCells = List.copyOf(reservedCells);
            lands = List.copyOf(lands);
        }
    }

    public RealmLandService(@Value("${daedalus.realm-layout.directory:}") String directory) {
        store = directory.isBlank() ? null : new RealmLayoutStore(Path.of(directory));
    }

    public District district(String realm, int district) {
        if (district < 0 || district >= 100) throw new IllegalArgumentException("District must be 0..99");
        if (realm == null || !RealmLayout.REALMS.contains(realm) || store == null) throw missing(realm);
        try {
            RealmLayout layout = store.load(realm).orElseThrow(() -> missing(realm));
            var rows = layout.district(district).stream().map(e -> new Land(e.landNumber(), e.x(), e.y(),
                    e.size(), Long.toString(e.seed()), (e.x() - LandGrid.HUB) * LandGrid.PITCH_M,
                    (e.y() - LandGrid.HUB) * LandGrid.PITCH_M)).toList();
            var reserved = layout.reservedCells().stream().filter(n -> LandGrid.district(n) == district).sorted().toList();
            return new District(1, realm, layout.revision(), district, LandGrid.SIDE, LandGrid.PITCH_M,
                    "east-north-realm-metres", reserved, rows);
        } catch (IOException ex) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "Realm layout unavailable", ex);
        }
    }

    private static ResourceNotFoundException missing(String realm) {
        return new ResourceNotFoundException("realm layout", realm, "No provisioned layout for this canonical realm");
    }
}
