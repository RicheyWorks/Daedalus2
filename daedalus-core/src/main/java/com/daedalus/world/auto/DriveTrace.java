// SPDX-License-Identifier: MIT

package com.daedalus.world.auto;

import com.daedalus.world.stamp.StampResult;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * Append-only log of driven capabilities. Account reads this; discover does not.
 */
public final class DriveTrace {

    /**
     * One driven step and the world revision after it returned.
     * {@code actor} is an account key — never a wallet type.
     */
    public record Step(String capability, String result, long revisionAfter, String actor) {

        public Step {
            Objects.requireNonNull(capability, "capability is required");
            Objects.requireNonNull(result, "result is required");
            actor = actor == null ? "" : actor;
        }

        public Step(String capability, String result, long revisionAfter) {
            this(capability, result, revisionAfter, "");
        }
    }

    private final List<Step> steps = new ArrayList<>();

    public void append(String capability, Object result, long revisionAfter) {
        append(capability, result, revisionAfter, "");
    }

    public void append(String capability, Object result, long revisionAfter, String actor) {
        String rendered = result == null ? "null"
                : result instanceof StampResult stamp ? stamp.outcome()
                : result.toString();
        steps.add(new Step(capability, rendered, revisionAfter, actor));
    }

    public List<Step> steps() {
        return List.copyOf(steps);
    }

    public int size() {
        return steps.size();
    }
}
