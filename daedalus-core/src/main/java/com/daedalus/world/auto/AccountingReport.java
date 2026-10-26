// SPDX-License-Identifier: MIT

package com.daedalus.world.auto;

import java.util.Objects;
import java.util.Set;
import java.util.TreeSet;

/** Discover vs drive. {@link #unaccounted()} must be 0. */
public final class AccountingReport {

    private final Set<String> discovered;
    private final Set<String> driven;
    private final Set<String> unaccounted;

    public AccountingReport(Set<String> discovered, Set<String> driven) {
        this.discovered = Set.copyOf(Objects.requireNonNull(discovered));
        this.driven = Set.copyOf(Objects.requireNonNull(driven));
        TreeSet<String> missing = new TreeSet<>(this.discovered);
        missing.removeAll(this.driven);
        this.unaccounted = Set.copyOf(missing);
    }

    public Set<String> discovered() {
        return discovered;
    }

    public Set<String> driven() {
        return driven;
    }

    public Set<String> unaccounted() {
        return unaccounted;
    }

    public int unaccountedCount() {
        return unaccounted.size();
    }
}
