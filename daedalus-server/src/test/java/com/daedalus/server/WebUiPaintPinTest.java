// SPDX-License-Identifier: MIT

package com.daedalus.server;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Pins leftover-drag paint on the static well without extending
 * {@link WebUiSmokeTest}'s fluent chain (javac overflows that tree).
 */
class WebUiPaintPinTest {

    @Test
    void leftoverDragPinsStayOnGoldNews() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html).contains(
                    "#log .t { color: #b09a72; margin-right: 6px; -webkit-user-drag: none")
                    .contains("#log .solver { color: #d4a04c; -webkit-user-drag: none")
                    .contains("#log .player { color: var(--gold); -webkit-user-drag: none")
                    .contains("#log .state  { color: var(--accent); -webkit-user-drag: none")
                    .contains("#log .err    { color: var(--warn); -webkit-user-drag: none")
                    .contains("#asciiOut .rock { color: #8c764e; -webkit-user-drag: none")
                    .contains("#asciiOut .gate { color: #3ee08f; -webkit-user-drag: none")
                    .contains("#asciiOut .exit { color: #ff5a5f; -webkit-user-drag: none")
                    .contains("#compareBox .gave-up { color: var(--warn); -webkit-user-drag: none")
                    .contains("#compareBox tr.pinned { background: #1a1610; -webkit-user-drag: none")
                    .contains("#compareBox tr.solver-row { cursor: pointer; -webkit-user-drag: none")
                    .contains("#compareBox tr.solver-row:hover { background: #1a1610; -webkit-user-drag: none")
                    .contains("#compareBox tr.pinned:hover { box-shadow: inset 3px 0 0 rgba(184, 133, 56, 0.95); -webkit-user-drag: none")
                    .contains("#gate .lede { color: #b09a72; cursor: text; margin: 0 0 22px; max-width: 34rem; font-size: 15px; -webkit-user-drag: none")
                    .contains("#gate article p { margin: 0; color: #b09a72; cursor: text; font-size: 13px; flex: 1; -webkit-user-drag: none")
                    .contains("details .hint { cursor: text; -webkit-user-drag: none")
                    .contains("#lb span { color: #b09a72; -webkit-user-drag: none")
                    .contains("#lb .rank { display: inline-block; width: 18px; color: #b09a72; -webkit-user-drag: none")
                    .contains("#lb b { color: #f2ead8; -webkit-user-drag: none")
                    .contains("#lb .score { color: var(--accent); font-weight: 700; -webkit-user-drag: none");
        }
    }
}
