// SPDX-License-Identifier: MIT

package com.daedalus.world.auto;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * Append-only log of driven capabilities. Account reads this; discover does not.
 */
public final class DriveTrace {

    /**
     * One driven step and the world revision after it returned.
     */
    public record Step(String capability, String result, long revisionAfter) {

        public Step {
            Objects.requireNonNull(capability, "capability is required");
            Objects.requireNonNull(result, "result is required");
        }
    }

    private final List<Step> steps = new ArrayList<>();

    public void append(String capability, Object result, long revisionAfter) {
        String rendered = result == null ? "null" : result.toString();
        steps.add(new Step(capability, rendered, revisionAfter));
    }

    public List<Step> steps() {
        return List.copyOf(steps);
    }

    public int size() {
        return steps.size();
    }
}
