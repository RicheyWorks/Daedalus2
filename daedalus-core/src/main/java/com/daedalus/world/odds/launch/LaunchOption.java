// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.launch;

import java.util.Objects;

/** One launch the Keeper can chalk: route index and name, days to wait, and expected life brought home. */
public record LaunchOption(int route, String routeName, int day, double expectedLife) {
    public LaunchOption {
        Objects.requireNonNull(routeName, "routeName");
        if (route < 0 || day < 0) {
            throw new IllegalArgumentException("route and day must be >= 0");
        }
    }
}
