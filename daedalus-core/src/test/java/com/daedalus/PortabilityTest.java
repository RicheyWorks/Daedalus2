// SPDX-License-Identifier: MIT
package com.daedalus;

import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;

/**
 * Portability (ADR-036): daedalus-core is the part of Daedalus that goes everywhere: the server, the
 * desktop, the plugin runtime, and (through the C++ and Python ports) Unreal and Blender. So it imports
 * nothing but the JDK and itself. A framework import here would tie every game rule, mesher and maze to
 * that framework.
 */
class PortabilityTest {

    private static final List<String> ALLOWED = List.of("java.", "com.daedalus.");

    @Test
    void coreImportsOnlyTheJdkAndItself() throws IOException {
        Path src = Path.of("src", "main", "java");
        assertTrue(Files.isDirectory(src), "run from the daedalus-core module: " + src.toAbsolutePath());
        List<String> foreign = new ArrayList<>();
        int files;
        try (Stream<Path> walk = Files.walk(src)) {
            List<Path> java = walk.filter(p -> p.toString().endsWith(".java")).toList();
            files = java.size();
            for (Path f : java) {
                int n = 0;
                for (String line : Files.readAllLines(f, StandardCharsets.UTF_8)) {
                    n++;
                    String t = line.strip();
                    if (!t.startsWith("import ")) {
                        continue;
                    }
                    String name = t.substring("import ".length()).replace("static ", "").strip();
                    if (ALLOWED.stream().noneMatch(name::startsWith)) {
                        foreign.add(src.relativize(f) + ":" + n + " " + name);
                    }
                }
            }
        }
        assertTrue(files > 100, "expected the whole core, found " + files + " files");
        assertTrue(foreign.isEmpty(), "daedalus-core must stay portable (JDK only):\n" + String.join("\n", foreign));
    }
}
