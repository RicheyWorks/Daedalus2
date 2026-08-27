// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.model.Point;

import java.util.ArrayList;
import java.util.List;
import java.util.function.BiConsumer;

/**
 * Cell-change tape a {@code GameSession} move can replay. The 3D host is
 * another view — it does not own a second sim.
 */
public final class ExploreSession {

    public record Step(Point from, Point to) {
    }

    private final List<Step> steps = new ArrayList<>();
    private BiConsumer<Point, Point> onStep;

    public void onStep(BiConsumer<Point, Point> listener) {
        this.onStep = listener;
    }

    public void record(Point from, Point to) {
        if (from == null || to == null || from.equals(to)) {
            return;
        }
        steps.add(new Step(from, to));
        if (onStep != null) {
            onStep.accept(from, to);
        }
    }

    public List<Step> steps() {
        return List.copyOf(steps);
    }

    public String moveJson(Point to) {
        if (to == null) {
            return "{\"to\":null}";
        }
        return "{\"to\":{\"row\":" + to.row() + ",\"col\":" + to.col() + "}}";
    }
}
