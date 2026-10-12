// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox;

import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.Test;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Runs the jukebox sound engine's node tests (src/test/js: the always-on limiter, EQ/gain/filter, keyboard voices,
 * fuzz) as part of the Maven build. Skipped, not failed, on a machine without node.
 */
class JukeboxAudioJsTest {

    @Test
    void theSoundEngineTestsPass() throws Exception {
        Process p;
        try {
            p = new ProcessBuilder("node", "--test", "src/test/js/").directory(new File(".")).redirectErrorStream(true).start();
        } catch (java.io.IOException e) {
            Assumptions.abort("node is not installed");
            return;
        }
        boolean done = p.waitFor(120, TimeUnit.SECONDS);
        String out = new String(p.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        assertThat(done).isTrue();
        assertThat(p.exitValue()).as(out).isZero();
        assertThat(out).contains("# fail 0");
    }
}
