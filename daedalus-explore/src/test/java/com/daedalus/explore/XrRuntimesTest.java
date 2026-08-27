// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class XrRuntimesTest {

    @Test
    void zeroJarsIsAValidDesktop() {
        assertThat(XrRuntimes.firstPresent(XrRuntime.class.getClassLoader())).isEmpty();
        assertThat(XrRuntimes.load(null)).isEmpty();
    }

    @Test
    void aPresentRuntimeIsSelected() throws Exception {
        try (URLClassLoader loader = loaderFor(FakePresentXr.class)) {
            List<XrRuntime> found = XrRuntimes.load(loader);
            assertThat(found).isNotEmpty();
            assertThat(XrRuntimes.firstPresent(loader)).isPresent();
            XrRuntime runtime = XrRuntimes.firstPresent(loader).orElseThrow();
            runtime.attach(null);
            assertThat(runtime.beginFrame()).isEqualTo(XrFrame.none());
            runtime.endFrame(XrFrame.none());
            runtime.stop();
            assertThat(runtime.id()).isEqualTo("fake-present");
        }
    }

    @Test
    void anAbsentRuntimeIsIgnored() throws Exception {
        try (URLClassLoader loader = loaderFor(FakeAbsentXr.class)) {
            assertThat(XrRuntimes.firstPresent(loader)).isEmpty();
        }
    }

    private static URLClassLoader loaderFor(Class<? extends XrRuntime> type) throws IOException {
        Path dir = Files.createTempDirectory("daedalus-xr");
        Path meta = dir.resolve("META-INF/services/com.daedalus.explore.XrRuntime");
        Files.createDirectories(meta.getParent());
        Files.writeString(meta, type.getName() + "\n", StandardCharsets.UTF_8);
        return new URLClassLoader(new URL[] {dir.toUri().toURL()}, type.getClassLoader());
    }

    public static final class FakePresentXr implements XrRuntime {
        @Override
        public String id() {
            return "fake-present";
        }

        @Override
        public boolean present() {
            return true;
        }
    }

    public static final class FakeAbsentXr implements XrRuntime {
        @Override
        public String id() {
            return "fake-absent";
        }

        @Override
        public boolean present() {
            return false;
        }
    }
}
