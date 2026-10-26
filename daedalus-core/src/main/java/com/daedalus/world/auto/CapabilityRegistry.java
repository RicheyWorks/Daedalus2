// SPDX-License-Identifier: MIT

package com.daedalus.world.auto;

import java.util.LinkedHashSet;
import java.util.Set;

/**
 * Discovery surface. Not the drive table — a capability listed here and never
 * driven is {@code UNACCOUNTED}.
 */
public final class CapabilityRegistry {

    private final LinkedHashSet<String> capabilities = new LinkedHashSet<>();

    public CapabilityRegistry register(String id) {
        if (id == null || id.isBlank()) {
            throw new IllegalArgumentException("Capability id is required");
        }
        capabilities.add(id);
        return this;
    }

    public Set<String> discover() {
        return Set.copyOf(capabilities);
    }
}
