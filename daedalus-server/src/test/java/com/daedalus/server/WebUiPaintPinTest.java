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
                    .contains("#asciiOut .rock { color: #8c764e; -webkit-user-drag: none; text-shadow: 0 1px 0 #2a2218")
                    .contains("max-height: 22vh; color: #d4c4a8; cursor: text; text-shadow: 0 1px 0 #2a2218")
                    .contains("#asciiOut .gate { color: #3ee08f; -webkit-user-drag: none; text-shadow: none")
                    .contains("#asciiOut .exit { color: #ff5a5f; -webkit-user-drag: none; text-shadow: none")
                    .contains("background: radial-gradient(circle at 50% 35%, #16120e 38%, #0c0908)")
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
                    .contains("fogWash.addColorStop(1, COLORS.unseen)");
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
                    .contains("/world/\" + WORLD + \"/parcels")
                    .contains("/world/\" + WORLD + \"/chunk?x=0&y=0&z=0");
            assertThat(html).contains("#worldBox .place { color: #94612e; -webkit-user-drag: none")
                    .contains("#worldBox .slab { color: #94612e; -webkit-user-drag: none");
            assertThat(world).contains("ink.className = named ? \"place\" : \"slab\"")
                    .contains("label === \"place\"")
                    .contains("chunk.occupied > 0");
            assertThat(world).doesNotContain("/maze/");
            assertThat(live).contains("/topic/world/world-zero/events")
                    .contains("host.onWorldEvent");
        }
    }
}
