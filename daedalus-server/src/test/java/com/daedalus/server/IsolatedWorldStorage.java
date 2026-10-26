// SPDX-License-Identifier: MIT
package com.daedalus.server;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.springframework.test.context.DynamicPropertyRegistry;

/** Test-only per-context disk state; production-profile tests must not mount developer saves. */
public final class IsolatedWorldStorage {
    private IsolatedWorldStorage() { }

    public static void register(DynamicPropertyRegistry registry) {
        final Path directory;
        try {
            directory = Files.createTempDirectory("daedalus-prod-test-");
        } catch (IOException ex) {
            throw new IllegalStateException("Cannot isolate production-profile test storage", ex);
        }
        // Capture once: a property lookup must never allocate a different world or sidecar directory.
        Path file = directory.resolve("world-zero.daew");
        registry.add("daedalus.world.file", file::toString);
    }
}
