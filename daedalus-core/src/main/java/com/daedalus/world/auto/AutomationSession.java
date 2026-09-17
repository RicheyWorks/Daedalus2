// SPDX-License-Identifier: MIT

package com.daedalus.world.auto;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.World;

import java.util.List;
import java.util.Objects;

/**
 * One automation run: address → drive → observe → trace. Discovery and
 * accounting stay on {@link CapabilityRegistry} and {@link AccountingHarness}.
 */
public final class AutomationSession {

    private final World world;
    private final DriveTrace log = new DriveTrace();
    private WorldAddress address;

    public AutomationSession(World world) {
        this.world = Objects.requireNonNull(world, "World is required");
    }

    public WorldAddress address(BlockCoordinate at) {
        this.address = new WorldAddress(world.id(),
                Objects.requireNonNull(at, "BlockCoordinate is required"));
        return this.address;
    }

    public WorldAddress address() {
        return address;
    }

    public Object drive(String capability, BlockType type) {
        if (address == null) {
            throw new IllegalStateException("Address a block before driving");
        }
        Object result = WorldOps.drive(world, capability, address.at(), type);
        log.append(capability, result, world.revision().value());
        return result;
    }

    public Observation observe() {
        if (address == null) {
            throw new IllegalStateException("Address a block before observing");
        }
        return Observation.take(world, address);
    }

    /** Snapshot of driven steps. The live log stays inside the session. */
    public List<DriveTrace.Step> trace() {
        return log.steps();
    }
}
