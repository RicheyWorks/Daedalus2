// SPDX-License-Identifier: MIT

package com.daedalus.desktop;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;

/**
 * Smoke-tests {@link DaedalusLauncher}'s static lifecycle accessors. We don't actually
 * boot Spring or JavaFX here — that's exercised by running the app — but we do lock in
 * the contract that:
 *
 * <ul>
 *   <li>{@code springContext()} is {@code null} before {@code main()} runs, and</li>
 *   <li>{@code shutdown()} is a safe no-op when the context was never built.</li>
 * </ul>
 *
 * <p>This guards against a regression where a half-finished launch (e.g. JavaFX failing
 * to find the platform-native libs) would NPE on the way back out.
 */
class DaedalusLauncherTest {

    @Test
    void shutdownIsNullSafe_beforeBoot() {
        // Note: relies on test isolation — Surefire forks per module by default, and no other
        // test in this module touches DaedalusLauncher. If that changes, swap this for a
        // reflection-based reset of the static field.
        assertThat(DaedalusLauncher.springContext()).isNull();
        assertThatCode(DaedalusLauncher::shutdown).doesNotThrowAnyException();
        assertThat(DaedalusLauncher.springContext()).isNull();
    }
}
