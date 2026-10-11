// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.ServiceLoader;

/** Discovers {@link XrRuntime} implementations. None is a valid desktop. */
public final class XrRuntimes {

    private XrRuntimes() {
    }

    public static List<XrRuntime> load(ClassLoader loader) {
        ClassLoader use = loader == null ? XrRuntime.class.getClassLoader() : loader;
        List<XrRuntime> found = new ArrayList<>();
        for (XrRuntime runtime : ServiceLoader.load(XrRuntime.class, use)) {
            found.add(runtime);
        }
        return List.copyOf(found);
    }

    public static Optional<XrRuntime> firstPresent(ClassLoader loader) {
        for (XrRuntime runtime : load(loader)) {
            if (runtime.present()) {
                return Optional.of(runtime);
            }
        }
        return Optional.empty();
    }
}
