// SPDX-License-Identifier: MIT

package com.daedalus.world.crafting;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** A reusable recipe matching economy/v0's item/n components and station ID.
 * Seconds are descriptive metadata; this core module does not schedule work. */
public record Recipe(String id, String station, int seconds,
                     List<Component> inputs, List<Component> outputs) {

    public Recipe {
        id = requireId(id, "recipe id");
        station = requireId(station, "station");
        if (seconds < 0) throw new IllegalArgumentException("seconds must be nonnegative");
        inputs = aggregate(inputs, "inputs");
        outputs = aggregate(outputs, "outputs");
    }

    /** A positive item quantity. Repeated items in a recipe are added together. */
    public record Component(String item, int n) {
        public Component {
            item = requireId(item, "item");
            if (n <= 0) throw new IllegalArgumentException("component quantity must be positive");
        }
    }

    static String requireId(String value, String label) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(label + " must not be blank");
        }
        return value;
    }

    private static List<Component> aggregate(List<Component> values, String label) {
        if (values == null || values.isEmpty()) {
            throw new IllegalArgumentException(label + " must not be empty");
        }
        Map<String, Integer> totals = new LinkedHashMap<>();
        for (Object value : values) {
            if (!(value instanceof Component component)) {
                throw new IllegalArgumentException(label + " contains an invalid component");
            }
            try {
                totals.put(component.item(), Math.addExact(totals.getOrDefault(component.item(), 0), component.n()));
            } catch (ArithmeticException overflow) {
                throw new IllegalArgumentException(label + " quantity overflows for " + component.item(), overflow);
            }
        }
        List<Component> result = new ArrayList<>();
        totals.forEach((item, count) -> result.add(new Component(item, count)));
        return List.copyOf(result);
    }
}
