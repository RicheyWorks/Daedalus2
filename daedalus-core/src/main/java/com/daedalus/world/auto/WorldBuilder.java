// SPDX-License-Identifier: MIT

package com.daedalus.world.auto;

import com.daedalus.engine.MazeGrid;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.World;

import java.util.List;
import java.util.Objects;
import java.util.Set;

/**
 * Agent builder client. Recipes call {@link WorldOps} through
 * {@link AutomationSession}. No parallel verb set, no wallet types.
 */
public final class WorldBuilder {

    public record Step(BlockCoordinate at, String capability, BlockType type, MazeGrid maze) {
        public Step {
            Objects.requireNonNull(at, "BlockCoordinate is required");
            Objects.requireNonNull(capability, "capability is required");
        }

        public Step(BlockCoordinate at, String capability, BlockType type) {
            this(at, capability, type, null);
        }
    }

    private final AutomationSession session;
    private final Set<String> allowed;

    public WorldBuilder(World world) {
        this(world, WorldZeroDrive.DRIVEN);
    }

    public WorldBuilder(World world, Set<String> allowed) {
        this.session = new AutomationSession(world);
        this.allowed = Set.copyOf(Objects.requireNonNull(allowed, "allowed"));
    }

    public AutomationSession session() {
        return session;
    }

    public Object run(Step step) {
        if (step == null) {
            throw new IllegalArgumentException("Step is required");
        }
        if (!allowed.contains(step.capability())) {
            throw new IllegalArgumentException("Unknown capability " + step.capability());
        }
        session.address(step.at());
        return session.drive(step.capability(), step.type(), step.maze());
    }

    public List<DriveTrace.Step> run(List<Step> recipe) {
        if (recipe == null) {
            throw new IllegalArgumentException("Recipe is required");
        }
        for (Step step : recipe) {
            run(step);
        }
        return session.trace();
    }
}
