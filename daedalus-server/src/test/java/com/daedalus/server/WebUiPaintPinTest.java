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
                    .contains("#asciiOut .rock { color: #766442; -webkit-user-drag: none")
                    .contains("#asciiOut .rock { color: #766442; -webkit-user-drag: none; text-shadow: 0 1px 0 #2a2218")
                    .contains("max-height: 22vh; color: #afa088; cursor: text; text-shadow: 0 1px 0 #2a2218")
                    .contains("#asciiOut .gate { color: #3ab675; -webkit-user-drag: none; text-shadow: none")
                    .contains("#asciiOut .exit { color: #d04e4f; -webkit-user-drag: none; text-shadow: none")
                    .contains("background: radial-gradient(circle at 50% 35%, #16120e 38%, #0c0908)")
                    .contains("#asciiOut .gate { color: #3ab675; -webkit-user-drag: none")
                    .contains("#asciiOut .exit { color: #d04e4f; -webkit-user-drag: none")
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
                    .contains("#lb .score { color: var(--accent); font-weight: 700; -webkit-user-drag: none")
                    .contains("#stats span { color: #b09a72; -webkit-user-drag: none")
                    .contains(".info b { color: #f2ead8; font-weight: 600; -webkit-user-drag: none")
                    .contains("\"Trebuchet MS\", sans-serif; letter-spacing: .22em; -webkit-user-drag: none")
                    .contains("mark { background: rgba(184, 133, 56, 0.35); color: #f2ead8; -webkit-user-drag: none")
                    .contains("#labOut .hint { color: #b09a72; -webkit-user-drag: none")
                    .contains("#tourBox .hint { color: #b09a72; -webkit-user-drag: none")
                    .contains("#campaignBox .hint { color: #b09a72; -webkit-user-drag: none")
                    .contains("#pluginBox .hint { color: #b09a72; -webkit-user-drag: none")
                    .contains("#lb .hint { color: #b09a72; -webkit-user-drag: none")
                    .contains("#compareBox b { -webkit-user-drag: none")
                    .contains("#labOut b { -webkit-user-drag: none")
                    .contains("#campaignBox b { -webkit-user-drag: none")
                    .contains("#tourBox b { -webkit-user-drag: none")
                    .contains("#stats b { -webkit-user-drag: none")
                    .contains("#compareBox span { -webkit-user-drag: none");
        }
    }

    @Test
    void faviconWearsTheIdleMazeMark() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html).contains(
                    "rel=\"icon\" type=\"image/svg+xml\"")
                    .contains("fill='%230c0908'")
                    .contains("stroke='%23b88538'")
                    .contains("x='5' y='9' width='2' height='2' fill='%2315110d'")
                    .contains("x='13' y='13' width='2' height='2' fill='%2318130e'")
                    .contains("x='15' y='15' width='2' height='2' fill='%23484339'")
                    .contains("x='23' y='11' width='2' height='2' fill='%23423c32'")
                    .contains("x='7' y='11' width='2' height='2' fill='%233ee08f'")
                    .contains("x='23' y='19' width='2' height='2' fill='%23ff5a5f'");
        }
    }

    @Test
    void homeScreenPngWearsTheIdleMazeMark() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html).contains(
                    "g34gEhPiBSIXOxMQsjeFI3EhPiCCiDvbGgORk40REA0OCyAeh2iD")
                    .contains("rel=\"apple-touch-icon\"")
                    .contains("property=\"og:image\"")
                    .contains("name=\"twitter:image\"");
        }
    }

    @Test
    void maskIconWearsTheIdleMazeMark() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html).contains(
                    "rel=\"mask-icon\" color=\"#b88538\"")
                    .contains("fill-rule='evenodd' d='M0 0h32v32H0zM1 1h30v30H1z'")
                    .contains("x='5' y='9' width='22' height='2' fill='black'")
                    .contains("x='7' y='11' width='2' height='2' fill='black'")
                    .contains("x='23' y='19' width='2' height='2' fill='black'");
        }
    }

    @Test
    void installedWellManifestWearsTheIdleMazeMark() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html).contains(
                    "rel=\"manifest\" href=\"data:application/manifest+json,")
                    .contains("%22icons%22%3A%5B")
                    .contains("%2232x32%22")
                    .contains("%22purpose%22%3A%22any%22")
                    .contains("g34gEhPiBSIXOxMQsjeFI3EhPiCCiDvbGgORk40REA0OCyAeh2iD");
        }
    }

    @Test
    void wellStartAndGoalFloorsWashTowardTheEnds() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js).contains("const END_FLOOR_W = 0.42")
                    .contains("mixHex(base, COLORS.start, END_FLOOR_W)")
                    .contains("mixHex(base, COLORS.goal, END_FLOOR_W)")
                    .contains("mixHex(COLORS.floorDim, lit, lamp)")
                    .contains("endFloorInk(mixHex(lampFloor, COLORS.floorDim, 0.22 * edge), t)")
                    .contains("endFloorInk(mixHex(warm, COLORS.floorDim, 0.22 * edge), t)")
                    .contains("mixHex(COLORS.floorHi, COLORS.floorWarm, lamp * 0.28)")
                    .contains("endFloorInk(mixHex(lampHi, COLORS.floorDim, 0.22 * edge), t)")
                    .contains("endFloorInk(mixHex(hi, COLORS.floorDim, 0.22 * edge), t)");
        }
    }

    @Test
    void wellEmptyWordmarkHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("function emptyWordmarkInk")
                    .contains("mixHex(\"#f2ead8\", COLORS.floorDim, 0.22)")
                    .contains("g.fillStyle = emptyWordmarkInk()")
                    .doesNotContain("g.fillStyle = \"#f2ead8\"");
        }
    }

    @Test
    void wellEmptyWordmarkMintHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("function emptyWordmarkMintInk")
                    .contains("mixHex(COLORS.start, COLORS.floorDim, 0.22)")
                    .contains("glow.addColorStop(0, emptyWordmarkMintGlow(0.08 + 0.04 * wave))")
                    .contains("g.shadowColor = emptyWordmarkMintGlow(mintA)");
        }
    }

    @Test
    void wellEmptyWordmarkGoldHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("function emptyWordmarkGoldInk")
                    .contains("mixHex(\"#f5c14a\", COLORS.floorDim, 0.22)")
                    .contains("glow.addColorStop(0.55, emptyWordmarkGoldGlow(0.04 + 0.03 * wave))")
                    .contains("g.shadowColor = emptyWordmarkGoldGlow(goldA)");
        }
    }

    @Test
    void wellEmptyCaptionTitleHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("function emptyCaptionTitleInk")
                    .contains("mixHex(\"#b88538\", COLORS.floorDim, 0.22)")
                    .contains("g.fillStyle = emptyCaptionTitleGlow(0.72 + 0.18 * wave)");
        }
    }

    @Test
    void wellEmptyCaptionDetailHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("function emptyCaptionDetailInk")
                    .contains("mixHex(\"#8c764e\", COLORS.floorDim, 0.22)")
                    .contains("g.fillStyle = emptyCaptionDetailGlow(0.55 + 0.20 * wave)");
        }
    }

    @Test
    void wellStageRimHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("@keyframes stageRimBreath")
                    .contains("border-color: rgba(153, 111, 49, 0.48)")
                    .contains("0 0 18px rgba(153, 111, 49, 0.06)")
                    .contains("border-color: rgba(153, 111, 49, 0.72)")
                    .contains("0 0 28px rgba(153, 111, 49, 0.14)")
                    .contains("border: 1px solid rgba(153, 111, 49, 0.55)")
                    .doesNotContain("0 0 18px rgba(184, 133, 56, 0.06)")
                    .doesNotContain("0 0 28px rgba(184, 133, 56, 0.14)");
        }
    }

    @Test
    void wellBoardRimHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("@keyframes boardRimBreath")
                    .contains("0%, 100% { border-color: rgba(153, 111, 49, 0.36); }")
                    .contains("50% { border-color: rgba(153, 111, 49, 0.55); }")
                    .contains("border-color: rgba(153, 111, 49, 0.42)")
                    .doesNotContain("border-color: rgba(184, 133, 56, 0.42)");
        }
    }

    @Test
    void wellPanelRimHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("@keyframes panelRimBreath")
                    .contains("0%, 100% { border-color: rgba(153, 111, 49, 0.30); }")
                    .contains("50% { border-color: rgba(153, 111, 49, 0.48); }")
                    .contains("border: 1px solid rgba(153, 111, 49, 0.36)")
                    .contains(".panel { border-color: rgba(153, 111, 49, 0.36); }")
                    .doesNotContain("0%, 100% { border-color: rgba(184, 133, 56, 0.30); }");
        }
    }

    @Test
    void wellHeaderRimHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("@keyframes headerRimBreath")
                    .contains("0%, 100% { border-bottom-color: rgba(153, 111, 49, 0.38); }")
                    .contains("50% { border-bottom-color: rgba(153, 111, 49, 0.62); }")
                    .contains("border-bottom: 1px solid rgba(153, 111, 49, 0.45)")
                    .contains("header { border-bottom-color: rgba(153, 111, 49, 0.45); }")
                    .doesNotContain("0%, 100% { border-bottom-color: rgba(184, 133, 56, 0.38); }");
        }
    }

    @Test
    void wellExportsRimHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("@keyframes exportsRimBreath")
                    .contains("background: rgba(16, 11, 8, .78);\n"
                            + "                                border: 1px solid rgba(153, 111, 49, 0.36)")
                    .doesNotContain("border: 1px solid rgba(184, 133, 56, 0.36)");
        }
    }

    @Test
    void wellExportsHoverHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("border-color: rgba(153, 111, 49, 0.85); color: #f2ead8")
                    .contains("box-shadow: 0 0 12px rgba(153, 111, 49, 0.18)")
                    .doesNotContain("border-color: rgba(184, 133, 56, 0.85); color: #f2ead8");
        }
    }

    @Test
    void wellExportsFocusHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains(".exports a:focus-visible { outline: 2px solid rgba(153, 111, 49, 0.85); outline-offset: 1px; }")
                    .doesNotContain(".exports a:focus-visible { outline: 2px solid rgba(184, 133, 56, 0.85); outline-offset: 1px; }");
        }
    }

    @Test
    void wellTourFocusHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("#tourBox a:focus-visible { outline: 2px solid rgba(153, 111, 49, 0.85); outline-offset: 1px; }")
                    .doesNotContain("#tourBox a:focus-visible { outline: 2px solid rgba(184, 133, 56, 0.85); outline-offset: 1px; }");
        }
    }

    @Test
    void wellAsciiRockHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("#asciiOut .rock { color: #766442")
                    .doesNotContain("#asciiOut .rock { color: #8c764e");
        }
    }

    @Test
    void wellAsciiGateHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("#asciiOut .gate { color: #3ab675")
                    .doesNotContain("#asciiOut .gate { color: #3ee08f");
        }
    }

    @Test
    void wellAsciiExitHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("#asciiOut .exit { color: #d04e4f")
                    .doesNotContain("#asciiOut .exit { color: #ff5a5f");
        }
    }

    @Test
    void wellAsciiFloorHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("max-height: 22vh; color: #afa088; cursor: text")
                    .doesNotContain("max-height: 22vh; color: #d4c4a8");
        }
    }

    @Test
    void wellGateSampleHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("#gate pre { margin: 0; padding: 8px; background: #16120e; color: #afa088;")
                    .doesNotContain("#gate pre { margin: 0; padding: 8px; background: #16120e; color: #d4c4a8;");
        }
    }

    @Test
    void wellLabModelHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/lab.js")) {
            assertThat(in).as("well lab painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("stroke=\"#766442\" stroke-width=\"2\"")
                    .doesNotContain("stroke=\"#8c764e\" stroke-width=\"2\"");
        }
    }

    @Test
    void wellLabAxesHaveRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/lab.js")) {
            assertThat(in).as("well lab painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("stroke=\"rgba(153, 111, 49, 0.28)\"")
                    .doesNotContain("stroke=\"rgba(184, 133, 56, 0.28)\"");
        }
    }

    @Test
    void wellLabSeriesHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/lab.js")) {
            assertThat(in).as("well lab painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("const LAB_SERIES = \"#af8441\"")
                    .doesNotContain("const LAB_SERIES = \"#d4a04c\"");
        }
    }

    @Test
    void wellCaptionDistanceHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/caption.js")) {
            assertThat(in).as("well caption painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("color:#af8441")
                    .doesNotContain("color:#d4a04c");
        }
    }

    @Test
    void wellCaptionHardestHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/caption.js")) {
            assertThat(in).as("well caption painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("color:#c6a441")
                    .doesNotContain("color:#f2c94c");
        }
    }

    @Test
    void wellCaptionSanctuaryHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/caption.js")) {
            assertThat(in).as("well caption painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("color:#758c44\">${s.placements.length} sanctuaries")
                    .doesNotContain("color:#8aaa50\">${s.placements.length} sanctuaries");
        }
    }

    @Test
    void wellCaptionFingerprintHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/caption.js")) {
            assertThat(in).as("well caption painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("color:#758c44\">${escapeHtml(f.predictedGeneratorId)}")
                    .doesNotContain("color:#8aaa50\">${escapeHtml(f.predictedGeneratorId)}");
        }
    }

    @Test
    void wellCaptionFingerprintMismatchHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/caption.js")) {
            assertThat(in).as("well caption painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("color:#c49425\">${escapeHtml(f.predictedGeneratorId)}")
                    .doesNotContain("color:#f0b429\">${escapeHtml(f.predictedGeneratorId)}");
        }
    }

    @Test
    void wellCaptionArenaWinHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/caption.js")) {
            assertThat(in).as("well caption painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("color:#c49425\">${escapeHtml(w.id)}</b> wins the arena")
                    .doesNotContain("color:#f0b429\">${escapeHtml(w.id)}</b> wins the arena");
        }
    }

    @Test
    void wellCaptionDefaultWinHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/caption.js")) {
            assertThat(in).as("well caption painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("color:#c49425\">${escapeHtml(w.id)}</b> wins by default")
                    .doesNotContain("color:#f0b429\">${escapeHtml(w.id)}</b> wins by default");
        }
    }

    @Test
    void wellCaptionLensGoldHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/caption.js")) {
            assertThat(in).as("well caption painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("i === 1 ? \"#c6a441\"")
                    .contains("LENS_COLORS = [\"#e5484d\", \"#f2c94c\", \"#8aaa50\"]")
                    .doesNotContain("background:${LENS_COLORS[i]};margin-right:4px;");
        }
    }

    @Test
    void wellCaptionLensRustHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/caption.js")) {
            assertThat(in).as("well caption painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("i === 0 ? \"#bc4041\"")
                    .contains("LENS_COLORS = [\"#e5484d\", \"#f2c94c\", \"#8aaa50\"]")
                    .doesNotContain("background:${LENS_COLORS[i]};margin-right:4px;");
        }
    }

    @Test
    void wellCaptionLensMossHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/caption.js")) {
            assertThat(in).as("well caption painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("background:${i === 0 ? \"#bc4041\" : i === 1 ? \"#c6a441\" : \"#758c44\"}")
                    .contains("LENS_COLORS = [\"#e5484d\", \"#f2c94c\", \"#8aaa50\"]")
                    .doesNotContain("background:${i === 0 ? \"#bc4041\" : i === 1 ? \"#c6a441\" : LENS_COLORS[i]}");
        }
    }

    @Test
    void wellCaptionChokeHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/caption.js")) {
            assertThat(in).as("well caption painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("color:#9f6544\">${cp}")
                    .doesNotContain("color:#c07850\">${cp}");
        }
    }

    @Test
    void wellCaptionNotOptimalHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/caption.js")) {
            assertThat(in).as("well caption painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("color:#bc4041'>not optimal")
                    .doesNotContain("color:#e5484d'>not optimal");
        }
    }

    @Test
    void wellStartDiscHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("function startTileInk")
                    .contains("mixHex(COLORS.start, COLORS.floorDim, 0.22 * edge)")
                    .contains("endpoint(g, geom, start, startTileInk(2 * start.row + 1, 2 * start.col + 1, th, tw))")
                    .contains("endpoint(g, geom, {row: 0, col: 0}, startTileInk(1, 1, idleRows, idleCols))");
        }
    }

    @Test
    void wellGoalDiscHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("function goalTileInk")
                    .contains("mixHex(COLORS.goal, COLORS.floorDim, 0.22 * edge)")
                    .contains("goalTileInk(2 * scene.fog.goal.row + 1, 2 * scene.fog.goal.col + 1, th, tw)")
                    .contains("goalTileInk(2 * goal.row + 1, 2 * goal.col + 1, th, tw)")
                    .contains("endpoint(g, geom, {row: 2, col: 4}, goalTileInk(5, 9, idleRows, idleCols))");
        }
    }

    @Test
    void idleMarkStartAndGoalFloorsWashTowardTheEnds() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js).contains("const idleFloor = mixHex(COLORS.floor, COLORS.floorWarm, 0.28)")
                    .contains("(r === 1 && c === 1) ? \"S\" : (r === 5 && c === 9) ? \"G\"")
                    .contains("endFloorInk(mixHex(idleFloor, COLORS.floorDim, 0.22 * edge), end)")
                    .contains("const idleHi = mixHex(COLORS.floorHi, COLORS.floorWarm, 0.28)")
                    .contains("endFloorInk(mixHex(idleHi, COLORS.floorDim, 0.22 * edge), end)")
                    .contains("const idleWall = mixHex(COLORS.wall, COLORS.wallWarm, 0.28)")
                    .contains("mixHex(idleWall, COLORS.unseen, 0.28 * edge)")
                    .contains("mixHex(idleWallHi, COLORS.unseen, 0.28 * edge)");
        }
    }

    @Test
    void wellFogUnseenHasVoidPocket() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js).contains("if (scene.fog) {")
                    .contains("fogWash.addColorStop(0, \"#16120e\")")
                    .contains("fogWash.addColorStop(1, COLORS.unseen)")
                    .doesNotContain("g.fillStyle = mixHex(COLORS.wall, COLORS.wallWarm, 0.28)");
        }
    }

    @Test
    void wellHeatCellsHaveRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("mixHex(\"#e5484d\", COLORS.floorDim, 0.22 * hedge)")
                    .contains("const hedge = Math.min(1, Math.sqrt(hdx * hdx + hdy * hdy))")
                    .contains("paintWashOpenings(g, geom, tiles, (r, c) => hot.has(r + \",\" + c),")
                    .contains("(tr, tc) => heatInk(tr, tc, th, tw)")
                    .contains("const glowInk = heatInk(2 * h.row + 1, 2 * h.col + 1, th, tw)");
        }
    }

    @Test
    void wellDeadendDiscsHaveRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("mixHex(\"#c8a878\", COLORS.floorDim, 0.22 * edge)")
                    .contains("const endInk = deadendInk(p, th, tw)");
        }
    }

    @Test
    void wellChokeMarksHaveRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("mixHex(\"#c07850\", COLORS.floorDim, 0.22 * edge)")
                    .contains("const cutInk = chokeInk(tr, tc, th, tw)");
        }
    }

    @Test
    void wellSanctuaryMarksHaveRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("mixHex(\"#8aaa50\", COLORS.floorDim, 0.22 * edge)")
                    .contains("const safeInk = sanctuaryInk(p, th, tw)")
                    .contains("g.strokeStyle = heatInk(2 * w.row + 1, 2 * w.col + 1, th, tw)");
        }
    }

    @Test
    void wellGhostDiscsHaveRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("mixHex(COLORS.ghost, COLORS.floorDim, 0.22 * edge)")
                    .contains("const ink = ghostInk(p, th, tw)")
                    .contains("ghostDisc(g, geom, scene.ghost.pos, th, tw)");
        }
    }

    @Test
    void wellGhostTrailsHaveRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("function ghostTileInk(tr, tc, th, tw)")
                    .contains("(tr, tc) => ghostTileInk(tr, tc, th, tw)");
        }
    }

    @Test
    void wellHardestTrailsHaveRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("mixHex(\"#f2c94c\", COLORS.floorDim, 0.22 * edge)")
                    .contains("(tr, tc) => hardestTileInk(tr, tc, th, tw)")
                    .contains("hardestTileInk(2 * hardTip.row + 1, 2 * hardTip.col + 1, th, tw)");
        }
    }

    @Test
    void wellTourTrailsHaveRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("mixHex(\"#d4b06a\", COLORS.floorDim, 0.22 * edge)")
                    .contains("(tr, tc) => tourTileInk(tr, tc, th, tw)")
                    .contains("tourTileInk(2 * tourTip.row + 1, 2 * tourTip.col + 1, th, tw)");
        }
    }

    @Test
    void wellWaypointMarksHaveRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("mixHex(got ? \"#8aaa50\" : \"#f2c94c\", COLORS.floorDim, 0.22 * edge)")
                    .contains("const coinInk = waypointInk(w, th, tw, got)");
        }
    }

    @Test
    void wellVictoryMarksHaveRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("mixHex(\"#f0b429\", COLORS.floorDim, 0.22 * edge)")
                    .contains("const winInk = victoryInk(goal, th, tw)")
                    .contains("li === 0")
                    .contains("(tr, tc) => expansionTileInk(tr, tc, th, tw)")
                    .contains("(tr, tc) => victoryTileInk(tr, tc, th, tw)");
        }
    }

    @Test
    void wellSessionWalkerHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("const standHex = PLAYER_COLORS[i % PLAYER_COLORS.length]")
                    .contains("trailTileInk(standHex, 2 * p.row + 1, 2 * p.col + 1, th, tw)");
        }
    }

    @Test
    void wellFogWalkerHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("const fogWalker = scene.fog.position")
                    .contains("playerTileInk(2 * fogWalker.row + 1, 2 * fogWalker.col + 1, th, tw)");
        }
    }

    @Test
    void wellSessionTrailsHaveRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("mixHex(hex, COLORS.floorDim, 0.22 * edge)")
                    .contains("(tr, tc) => trailTileInk(trailHex, tr, tc, th, tw)");
        }
    }

    @Test
    void wellFogWalkHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("mixHex(\"#f5c14a\", COLORS.floorDim, 0.22 * edge)")
                    .contains("(tr, tc) => playerTileInk(tr, tc, th, tw)");
        }
    }

    @Test
    void wellRaceAWashHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("g.fillStyle = li === 0")
                    .contains("? expansionTileInk(2 * p.row + 1, 2 * p.col + 1, th, tw)")
                    .contains("li === 0")
                    .contains("(tr, tc) => expansionTileInk(tr, tc, th, tw)")
                    .doesNotContain("g.fillStyle = lane.color;");
        }
    }

    @Test
    void wellRaceRibbonHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("pathHead(g, geom, raceTip, li === 0")
                    .contains("expansionTileInk(2 * raceTip.row + 1, 2 * raceTip.col + 1, th, tw)")
                    .contains("victoryTileInk(2 * raceTip.row + 1, 2 * raceTip.col + 1, th, tw)")
                    .contains("const raceHead = walkHead(lane.path, lane.pathProg)")
                    .contains("expansionTileInk(2 * raceHead.row + 1, 2 * raceHead.col + 1, th, tw)")
                    .contains("victoryTileInk(2 * raceHead.row + 1, 2 * raceHead.col + 1, th, tw)");
        }
    }

    @Test
    void wellPathRibbonHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("paintWalk(g, geom, scene.path, COLORS.path, scene.pathProgress, 0.85, \"ribbon\",")
                    .contains("(tr, tc) => expansionTileInk(tr, tc, th, tw)")
                    .contains("const pathTip = walkHead(scene.path, scene.pathProgress)")
                    .contains("expansionTileInk(2 * pathTip.row + 1, 2 * pathTip.col + 1, th, tw)");
        }
    }

    @Test
    void wellExpansionWashHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("mixHex(COLORS.path, COLORS.floorDim, 0.22 * edge)")
                    .contains("g.fillStyle = expansionTileInk(2 * p.row + 1, 2 * p.col + 1, th, tw)")
                    .contains("(tr, tc) => expansionTileInk(tr, tc, th, tw)")
                    .doesNotContain("g.fillStyle = COLORS.path;");
        }
    }

    @Test
    void wellFieldCellsHaveRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("mixHex(color, COLORS.floorDim, 0.22 * edge)")
                    .contains("g.fillStyle = fieldInk(s.color, r, c, th, tw)")
                    .contains("(tr, tc) => fieldOpenInk(tr, tc, th, tw, openColor)");
        }
    }

    @Test
    void wellLensCellsHaveRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("g.fillStyle = fieldInk(lensColors[band], r, c, th, tw)")
                    .contains("(tr, tc) => fieldOpenInk(tr, tc, th, tw, lensColors[2])");
        }
    }

    @Test
    void wellFogWallsHaveRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/draw.js")) {
            assertThat(in).as("well painter").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("const lampWall = mixHex(COLORS.wall, COLORS.wallWarm, lamp * 0.45)")
                    .contains("mixHex(lampWall, COLORS.unseen, 0.28 * edge)")
                    .contains("mixHex(lampHi, COLORS.unseen, 0.28 * edge)");
        }
    }

    @Test
    void wellLegendStoneChipsHaveRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("#legend [data-key=\"floor\"] i {")
                    .contains("radial-gradient(circle at 45% 40%, #484339 28%, #2a2218)")
                    .contains("#legend [data-key=\"wall\"] i {")
                    .contains("radial-gradient(circle at 45% 40%, #19140f 28%, #15110d)")
                    .contains("#legend [data-key=\"fog\"] i {")
                    .contains("radial-gradient(circle at 45% 40%, #16120e 28%, #0c0908)");
        }
    }

    @Test
    void wellLegendStartAndGoalChipsHaveRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("#legend [data-key=\"start\"] i {")
                    .contains("radial-gradient(circle at 45% 40%, #3ee08f 28%, #1e8a58)")
                    .contains("#legend [data-key=\"goal\"] i {")
                    .contains("radial-gradient(circle at 45% 40%, #ff5a5f 28%, #c4383c)")
                    .doesNotContain("background:#3ee08f;border-radius:50%")
                    .doesNotContain("background:#ff5a5f;border-radius:50%");
        }
    }

    @Test
    void wellLegendSanctuaryChipHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("#legend [data-key=\"sanctuary\"] i {")
                    .contains("radial-gradient(circle at 45% 40%, #8aaa50 28%, #4e6a28)")
                    .doesNotContain("background:#8aaa50;border-radius:50%");
        }
    }

    @Test
    void wellLegendGhostChipHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("#legend [data-key=\"ghost\"] i {")
                    .contains("radial-gradient(circle at 45% 40%, #e8e0d4 28%, #6a6258)")
                    .doesNotContain("background:#e8e0d4;border-radius:50%;opacity:.6");
        }
    }

    @Test
    void wellLegendChokeChipHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("#legend [data-key=\"choke\"] i {")
                    .contains("radial-gradient(circle at 45% 40%, #c07850 28%, #6a4030)")
                    .doesNotContain("background:#c07850\"");
        }
    }

    @Test
    void wellLegendDeadendChipHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("#legend [data-key=\"deadend\"] i {")
                    .contains("radial-gradient(circle at 45% 40%, #c8a878 28%, #6a5438)")
                    .doesNotContain("background:#c8a878\"");
        }
    }

    @Test
    void wellLegendPathChipHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("#legend [data-key=\"path\"] i {")
                    .contains("radial-gradient(circle at 45% 40%, #8fb8ff 28%, #3a5888)")
                    .doesNotContain("data-key=\"path\"><i style=\"background:#8fb8ff\"");
        }
    }

    @Test
    void wellLegendTourChipHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("#legend [data-key=\"tour\"] i {")
                    .contains("radial-gradient(circle at 45% 40%, #d4b06a 28%, #6a5428)")
                    .doesNotContain("data-key=\"tour\"><i style=\"background:#d4b06a\"");
        }
    }

    @Test
    void wellLegendHardestChipHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("#legend [data-key=\"hardest\"] i {")
                    .contains("radial-gradient(circle at 45% 40%, #f2c94c 28%, #8a6820)")
                    .doesNotContain("data-key=\"hardest\"><i style=\"background:#f2c94c\"");
        }
    }

    @Test
    void wellLegendPlayerChipsHaveRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("#legend [data-key=\"player\"] i:nth-child(1) {")
                    .contains("radial-gradient(circle at 45% 40%, #f5c14a 28%, #8a6418)")
                    .contains("radial-gradient(circle at 45% 40%, #e88868 28%, #8a3828)")
                    .contains("radial-gradient(circle at 45% 40%, #e8a060 28%, #8a5020)")
                    .contains("radial-gradient(circle at 45% 40%, #b8a058 28%, #6a5420)")
                    .doesNotContain("background:#f5c14a;border-radius:50%")
                    .doesNotContain("background:#e88868;border-radius:50%")
                    .doesNotContain("background:#e8a060;border-radius:50%")
                    .doesNotContain("background:#b8a058;border-radius:50%;margin-right:0");
        }
    }

    @Test
    void wellLegendWaypointChipHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("#legend [data-key=\"waypoint\"] i {")
                    .contains("transform: rotate(45deg)")
                    .contains("radial-gradient(circle at 45% 40%, #f2c94c 28%, #8a6820)")
                    .doesNotContain("data-key=\"waypoint\"><i style=\"background:#f2c94c;transform:rotate(45deg)\"");
        }
    }

    @Test
    void wellLegendHotspotChipHasRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("#legend [data-key=\"hotspot\"] i {")
                    .contains("radial-gradient(circle at 45% 40%, rgba(229,72,77,.5) 28%, rgba(106,32,36,.5))")
                    .doesNotContain("data-key=\"hotspot\"><i style=\"background:rgba(229,72,77,.5)\"");
        }
    }

    @Test
    void wellLegendRaceChipsHaveRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("#legend [data-key=\"race\"] i:nth-child(1) {")
                    .contains("radial-gradient(circle at 45% 40%, #8fb8ff 28%, #3a5888)")
                    .contains("radial-gradient(circle at 45% 40%, #f0b429 28%, #8a6018)")
                    .doesNotContain("data-key=\"race\"><i style=\"background:#8fb8ff;width:6px\"");
        }
    }

    @Test
    void wellLegendLensChipsHaveRimDepth() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/index.html")) {
            assertThat(in).as("static well page").isNotNull();
            String html = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html)
                    .contains("#legend [data-key=\"lens\"] i:nth-child(1) {")
                    .contains("radial-gradient(circle at 45% 40%, #e5484d 28%, #6a2024)")
                    .contains("radial-gradient(circle at 45% 40%, #f2c94c 28%, #8a6820)")
                    .contains("radial-gradient(circle at 45% 40%, #8aaa50 28%, #4e6a28)")
                    .doesNotContain("data-key=\"lens\"><i style=\"background:#e5484d;width:6px\"");
        }
    }

    @Test
    void wellWorldPanelListensBesideTheMaze() throws Exception {
        try (InputStream htmlIn = getClass().getResourceAsStream("/static/index.html");
             InputStream worldIn = getClass().getResourceAsStream("/static/world.js");
             InputStream liveIn = getClass().getResourceAsStream("/static/live.js")) {
            assertThat(htmlIn).as("static well page").isNotNull();
            assertThat(worldIn).as("world panel").isNotNull();
            assertThat(liveIn).as("stomp subscribe").isNotNull();
            String html = new String(htmlIn.readAllBytes(), StandardCharsets.UTF_8);
            String world = new String(worldIn.readAllBytes(), StandardCharsets.UTF_8);
            String live = new String(liveIn.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(html).contains("id=\"world\"")
                    .contains("id=\"worldBox\"")
                    .contains("<script src=\"/world.js\" defer></script>")
                    .contains("id=\"stage\"");
            assertThat(html).doesNotContain("location.hash = \"#world\"");
            assertThat(world).contains("const WORLD = \"world-zero\"")
                    .contains("host.api(\"/world/\" + WORLD)")
                    .contains("/world/\" + WORLD + \"/door")
                    .contains("/world/\" + WORLD + \"/trap")
                    .contains("/world/\" + WORLD + \"/portal")
                    .contains("/world/\" + WORLD + \"/npc")
                    .contains("/world/\" + WORLD + \"/chunk?x=0&y=0&z=0");
            assertThat(world).contains("row(box, \"lease\"")
                    .contains("world.lease")
                    .contains("row(box, \"leases\"")
                    .contains("world.leases")
                    .contains("row(box, \"maze\"")
                    .contains("world.maze")
                    .contains("row(box, \"mazes\"")
                    .contains("world.mazes")
                    .contains("row(box, \"plots\"")
                    .contains("world.plots")
                    .contains("row(box, \"street\"")
                    .contains("world.street")
                    .contains("row(box, \"lot\"")
                    .contains("world.lot")
                    .contains("row(box, \"lots\"")
                    .contains("world.lots")
                    .contains("row(box, \"box\"")
                    .contains("world.box")
                    .contains("row(box, \"boxes\"")
                    .contains("world.boxes")
                    .contains("world.place")
                    .contains("row(box, \"places\"")
                    .contains("world.places")
                    .contains("world.occupants")
                    .contains("row(box, \"occupants\"")
                    .contains("world.stands")
                    .contains("row(box, \"stands\"")
                    .contains("world.acl")
                    .contains("row(box, \"acl\"")
                    .contains("world.acls")
                    .contains("row(box, \"acls\"")
                    .contains("world.drive")
                    .contains("row(box, \"drive\"")
                    .contains("world.driveActor")
                    .contains("row(box, \"actor\"")
                    .contains("world.driveAt")
                    .contains("row(box, \"at\"");
            assertThat(world).doesNotContain("/world/\" + WORLD + \"/parcels\"");
            assertThat(html).contains("#worldBox .place { color: #94612e; -webkit-user-drag: none")
                    .contains("#worldBox .slab { color: #94612e; -webkit-user-drag: none");
            assertThat(world).contains("ink.className = named ? \"place\" : \"slab\"")
                    .contains("function occupancy")
                    .contains("obj.box")
                    .contains("obj.maze")
                    .contains("obj.lease")
                    .contains("obj.acl")
                    .contains("obj.drive")
                    .contains("obj.driveActor")
                    .contains("obj.driveAt")
                    .contains("door.place")
                    .contains("npc.place")
                    .contains("label === \"place\"")
                    .contains("label === \"places\"")
                    .contains("label === \"street\"")
                    .contains("chunk.occupied > 0")
                    .contains("chunk.place")
                    .contains("chunk.places")
                    .contains("chunk.street")
                    .contains("chunk.lot")
                    .contains("chunk.lots")
                    .contains("chunk.maze")
                    .contains("chunk.mazes")
                    .contains("chunk.lease")
                    .contains("chunk.leases")
                    .contains("chunk.acl")
                    .contains("chunk.acls")
                    .contains("chunk.box")
                    .contains("chunk.boxes")
                    .contains("chunk.occupants")
                    .contains("chunk.stands")
                    .contains("chunk.drive")
                    .contains("chunk.driveActor")
                    .contains("chunk.driveAt");
            assertThat(world).doesNotContain("/maze/");
            assertThat(world).contains("frame.place")
                    .contains("frame.lot")
                    .contains("frame.box")
                    .contains("frame.maze")
                    .contains("frame.lease")
                    .contains("frame.acl")
                    .contains("frame.occupant")
                    .contains("frame.drive")
                    .contains("frame.driveActor")
                    .contains("frame.driveAt");
            assertThat(live).contains("/topic/world/world-zero/events")
                    .contains("host.onWorldEvent");
        }
    }

    @Test
    void wellWorldAgentDrivesWorldOps() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/static/world.js")) {
            assertThat(in).as("world panel").isNotNull();
            String js = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js)
                    .contains("\"block.place\"")
                    .contains("\"trap.arm\"")
                    .contains("\"parcel.lease\"")
                    .contains("\"parcel.release\"")
                    .contains("\"parcel.grant\"")
                    .contains("\"parcel.deny\"")
                    .contains("\"parcel.revoke\"")
                    .contains("\"parcel.forgive\"")
                    .contains("\"stamp.apply\"")
                    .contains("/world/\" + WORLD + \"/parcels/lease")
                    .contains("/world/\" + WORLD + \"/parcels/release")
                    .contains("/world/\" + WORLD + \"/parcels/grant")
                    .contains("/world/\" + WORLD + \"/parcels/deny")
                    .contains("/world/\" + WORLD + \"/parcels/revoke")
                    .contains("/world/\" + WORLD + \"/parcels/forgive")
                    .contains("verb: type || \"block.place\"")
                    .contains("actorId: actor || \"alice\"")
                    .contains("/world/\" + WORLD + \"/stamp")
                    .contains("/world/\" + WORLD + \"/door/open\" + actorQuery(actor)")
                    .contains("/world/\" + WORLD + \"/door/close\" + actorQuery(actor)")
                    .contains("/world/\" + WORLD + \"/trap/arm\" + actorQuery(actor)")
                    .contains("/world/\" + WORLD + \"/trap/disarm\" + actorQuery(actor)")
                    .contains("/world/\" + WORLD + \"/portal/open\" + actorQuery(actor)")
                    .contains("/world/\" + WORLD + \"/portal/seal\" + actorQuery(actor)")
                    .contains("/world/\" + WORLD + \"/npc/talk\" + actorQuery(actor)")
                    .contains("/world/\" + WORLD + \"/npc/hush\" + actorQuery(actor)")
                    .contains("actorId=\" + encodeURIComponent(actor)")
                    .contains("actorQuery(actor, \"&\")")
                    .contains("step.path(cell, type)")
                    .contains("/world/\" + WORLD + \"/trace")
                    .contains("throw new Error(\"Unknown capability \" + capability)")
                    .contains("builder — WorldOps only")
                    .contains("lastStep.result")
                    .contains("world && world.driveActor")
                    .contains("world && world.driveAt")
                    .contains("host.state && host.state.maze && host.state.maze.id")
                    .contains("body.mazeId = mazeId")
                    .contains("body.next = true")
                    .contains("body.actorId = type")
                    .contains("body.actorId = actor")
                    .contains("drive(host, capability, at, type, actor)")
                    .contains("async function projectLab")
                    .contains("drive(host, \"stamp.apply\")")
                    .contains("drive(host, \"parcel.lease\")")
                    .contains("stamped = result && result.ok");
            assertThat(js).doesNotContain("\"agent.build\"");
            assertThat(js).doesNotContain("/maze/");
        }
        try (InputStream app = getClass().getResourceAsStream("/static/app.js")) {
            assertThat(app).as("well host").isNotNull();
            String js = new String(app.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js).contains("function worldHost()")
                    .contains("return {$, api, state};")
                    .contains("projectWorld() { return DaedalusWorld.projectLab(worldHost()); }");
        }
        try (InputStream mint = getClass().getResourceAsStream("/static/mint.js")) {
            assertThat(mint).as("generate mint").isNotNull();
            String js = new String(mint.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(js).contains("if (host.projectWorld)")
                    .contains("await host.projectWorld()");
        }
    }
}
