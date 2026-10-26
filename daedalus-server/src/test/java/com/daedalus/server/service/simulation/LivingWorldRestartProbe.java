// SPDX-License-Identifier: MIT
package com.daedalus.server.service.simulation;

import com.daedalus.world.WorldId;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.nio.file.Path;

/** Separate JVM fixture; the writer terminates without application cleanup after a committed action. */
public final class LivingWorldRestartProbe {
    private LivingWorldRestartProbe() { }
    public static void main(String[] args) throws Exception {
        var service = new LivingWorldService(new FileSimulationRepository(Path.of(args[1])), WorldId.ZERO, 0,
                "alice", 1000, () -> 1000, e -> { }, new SimpleMeterRegistry());
        var result = service.supply("world-zero", "alice", "00000000-0000-0000-0000-000000000001", 3);
        if (result.duplicate() != args[0].equals("read") || result.state().cisternWater() != 0
                || result.state().keeperWater() != 3 || !result.state().rememberedActor().equals("alice")) {
            throw new AssertionError("Restart changed transaction outcome");
        }
        System.out.println("RECOVERY_OK");
        System.out.flush();
        if (args[0].equals("write")) Runtime.getRuntime().halt(0);
        service.close();
    }
}
