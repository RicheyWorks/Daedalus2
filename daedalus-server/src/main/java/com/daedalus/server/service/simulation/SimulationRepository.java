// SPDX-License-Identifier: MIT
package com.daedalus.server.service.simulation;

import com.daedalus.world.simulation.SimulationCodec;
import java.io.IOException;

/** Persistence boundary: successful save must precede acknowledgment and publication. */
public interface SimulationRepository extends AutoCloseable {
    SimulationCodec.Stored load() throws IOException;
    void save(SimulationCodec.Stored state) throws IOException;
    @Override void close() throws IOException;
}
