// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.desktop.ui.themes.Theme;
import javafx.scene.paint.Color;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Smoke-tests the desktop module's bean wiring point — {@link ThemeManager} — without
 * spinning up a JavaFX {@code Toolkit}. Covers the three constructor branches that
 * decide which theme the app boots with:
 *
 * <ol>
 *   <li>The {@code daedalus.ui.theme} property names a registered theme → use it.</li>
 *   <li>The named default isn't registered → fall back to the first theme in the list.</li>
 *   <li>No themes registered at all → {@code active()} is {@code null}, no NPE.</li>
 * </ol>
 *
 * <p>The {@code apply(Scene, String)} path needs a JavaFX {@code Toolkit} and is exercised
 * end-to-end by running the desktop app. We intentionally don't pull in TestFX/Monocle just
 * to cover a five-line method.
 */
class ThemeManagerTest {

    @Test
    void defaultsToNamedTheme_whenPresent() {
        Theme cosmic = fakeTheme("cosmic");
        Theme noir   = fakeTheme("noir");

        ThemeManager mgr = new ThemeManager(List.of(cosmic, noir), "cosmic");

        assertThat(mgr.active()).isSameAs(cosmic);
        assertThat(mgr.byId("noir")).isSameAs(noir);
        assertThat(mgr.byId("does-not-exist")).isNull();
        assertThat(mgr.all()).containsExactlyInAnyOrder(cosmic, noir);
    }

    @Test
    void cosmicShellWearsGoldLipsAndBrandGlow() throws Exception {
        try (var in = ThemeManagerTest.class.getResourceAsStream("/ui/cosmic.css")) {
            assertThat(in).as("cosmic.css is on the classpath").isNotNull();
            String css = new String(in.readAllBytes());
            assertThat(css).contains("rgba(153, 111, 49, 0.45)");
            assertThat(css).doesNotContain("rgba(184, 133, 56, 0.45)");
            assertThat(css).contains("dropshadow(one-pass-box, rgba(62, 224, 143, 0.28)");
            assertThat(css).contains("rgba(62, 224, 143, 0.28), 14, 0.45, 0, 0);\n    -fx-cursor: default;");
            assertThat(css).contains("dropshadow(one-pass-box, rgba(153, 111, 49, 0.22)");
            assertThat(css).doesNotContain("dropshadow(one-pass-box, rgba(184, 133, 56, 0.22)");
            assertThat(css).contains("-fx-border-color: rgba(184, 133, 56, 0.85)");
            assertThat(css).contains("-fx-border-color: rgba(184, 133, 56, 0.28)");
            assertThat(css).contains("-fx-border-color: rgba(184, 133, 56, 0.32)");
            assertThat(css).contains("-fx-border-color: rgba(153, 111, 49, 0.36)");
            assertThat(css).doesNotContain("-fx-border-color: rgba(184, 133, 56, 0.36)");
            assertThat(css).contains(".status-bar");
            assertThat(css)
                    .as("desktop well wears the same inset void shade as web #stage")
                    .contains("innershadow(gaussian, rgba(0, 0, 0, 0.35), 48");
            assertThat(css).contains("-fx-focus-color: rgba(153, 111, 49, 0.85)");
            assertThat(css).doesNotContain("-fx-focus-color: rgba(184, 133, 56, 0.85)");
            assertThat(css).contains("-fx-faint-focus-color: rgba(153, 111, 49, 0.25)");
            assertThat(css).contains("-fx-faint-focus-color: rgba(153, 111, 49, 0.25);\n    -fx-cursor: default;");
            assertThat(css).doesNotContain("-fx-faint-focus-color: rgba(184, 133, 56, 0.25)");
            assertThat(css).contains("#16120e");
            assertThat(css).contains("#0c0908");
            assertThat(css).contains("-fx-background-color: #0c0908");
            assertThat(css).contains("-fx-highlight-fill: rgba(153, 111, 49, 0.35)");
            assertThat(css).doesNotContain("-fx-highlight-fill: rgba(184, 133, 56, 0.35)");
            assertThat(css).contains("-fx-highlight-text-fill: #f2ead8");
            assertThat(css).contains("-fx-font-smoothing-type: gray");
            assertThat(css).contains("-fx-font-smoothing-type: gray;\n    -fx-text-fill: #f2ead8;");
            assertThat(css).contains("-fx-font-smoothing-type: gray;\n    -fx-text-fill: #f2ead8;\n    -fx-cursor: default;");
            assertThat(css).contains(".toolbar");
            assertThat(css).contains("-fx-border-width: 0 0 1 0;\n    -fx-cursor: default;");
            assertThat(css).contains(".toolbar .brand");
            assertThat(css).contains(".toolbar .label");
            assertThat(css).contains(".toolbar .label {\n    -fx-text-fill: #b09a72;");
            assertThat(css).contains(".toolbar .label {\n    -fx-text-fill: #b09a72;\n    -fx-cursor: default;");
            assertThat(css).contains("-fx-text-fill: #f2ead8");
            assertThat(css).contains(".status-bar");
            assertThat(css).contains(".status-bar .label");
            assertThat(css).contains("-fx-font-size: 12px;\n    -fx-cursor: default;");
            assertThat(css).contains("-fx-border-width: 1 0 0 0;\n    -fx-cursor: default;");
            assertThat(css).contains("-fx-background-color: #16120e");
            assertThat(css).contains("rgba(16, 11, 8, 0.55)");
            assertThat(css).contains("rgba(16, 11, 8, 0.92)");
            assertThat(css).contains("rgba(16, 11, 8, 0.92));\n    -fx-cursor: default;");
            assertThat(css).contains(".legend .label");
            assertThat(css).contains("-fx-font-weight: bold;\n    -fx-cursor: default;");
            assertThat(css).contains("#b09a72");
            assertThat(css).contains(".exports .button");
            assertThat(css).contains("-fx-padding: 0;\n    -fx-cursor: default;");
            assertThat(css).contains("rgba(16, 11, 8, 0.78)");
            assertThat(css).contains(".exports .button:hover");
            assertThat(css).contains("-fx-background-color: #1a1610");
        }
        try (var in = ThemeManagerTest.class.getResourceAsStream("/ui/main.fxml")) {
            assertThat(in).as("main.fxml is on the classpath").isNotNull();
            String fxml = new String(in.readAllBytes());
            assertThat(fxml).contains("stroke=\"rgba(242,234,216,0.28)\"");
            assertThat(fxml).contains("stroke=\"rgba(245,193,74,0.35)\"");
            assertThat(fxml).contains("stroke=\"rgba(229,72,77,0.35)\"");
            assertThat(fxml).contains("color=\"#484339\"");
            assertThat(fxml).contains("color=\"#2a2218\"");
            assertThat(fxml).contains("legendStart");
            assertThat(fxml).contains("<RadialGradient centerX=\"0.45\" centerY=\"0.40\" radius=\"1.0\"");
            assertThat(fxml).contains("color=\"#19140f\"");
            assertThat(fxml).contains("color=\"#15110d\"");
            assertThat(fxml).contains("color=\"#16120e\"");
            assertThat(fxml).contains("color=\"#0c0908\"");
            assertThat(fxml).contains("color=\"#3ee08f\"");
            assertThat(fxml).contains("color=\"#1e8a58\"");
            assertThat(fxml).contains("color=\"#ff5a5f\"");
            assertThat(fxml).contains("color=\"#c4383c\"");
            assertThat(fxml).doesNotContain("fill=\"#3ee08f\"");
            assertThat(fxml).doesNotContain("fill=\"#ff5a5f\"");
            assertThat(fxml).doesNotContain("fill=\"#c07850\"");
            assertThat(fxml).contains("color=\"#c07850\"");
            assertThat(fxml).contains("color=\"#6a4030\"");
            assertThat(fxml).contains("color=\"#c8a878\"");
            assertThat(fxml).contains("color=\"#6a5438\"");
            assertThat(fxml).doesNotContain("fill=\"#c8a878\"");
            assertThat(fxml).doesNotContain("fill=\"#8aaa50\"");
            assertThat(fxml).contains("color=\"#8aaa50\"");
            assertThat(fxml).contains("color=\"#4e6a28\"");
            assertThat(fxml).contains("legendDeadend");
            assertThat(fxml).contains("legendHardest");
            assertThat(fxml).contains("color=\"#c6a441\"");
            assertThat(fxml).contains("color=\"#f2c94c\"");
            assertThat(fxml).contains("color=\"#8a6820\"");
            assertThat(fxml).doesNotContain("fill=\"#f2c94c\" arcWidth=\"3\" arcHeight=\"3\"");
            assertThat(fxml).contains("legendWaypoint");
            assertThat(fxml).doesNotContain("fill=\"#f2c94c\" rotate=\"45\"");
            assertThat(fxml).contains("legendHotspot");
            assertThat(fxml).contains("color=\"#e5484d\"");
            assertThat(fxml).contains("color=\"#6a2024\"");
            assertThat(fxml).doesNotContain("fill=\"#e5484d\" opacity=\"0.5\"");
            assertThat(fxml).contains("legendTour");
            assertThat(fxml).doesNotContain("fill=\"#d4b06a\"");
            assertThat(fxml).contains("color=\"#af9158\"");
            assertThat(fxml).doesNotContain("color=\"#d4b06a\"");
            assertThat(fxml).contains("color=\"#6a5428\"");
            assertThat(fxml).doesNotContain("fill=\"#d4b06a\" arcWidth=\"3\" arcHeight=\"3\"");
            assertThat(fxml).contains("legendPath");
            assertThat(fxml).contains("color=\"#8fb8ff\"");
            assertThat(fxml).contains("color=\"#3a5888\"");
            assertThat(fxml).doesNotContain("fill=\"#8fb8ff\" arcWidth=\"3\" arcHeight=\"3\"");
            assertThat(fxml).contains("legendRace");
            assertThat(fxml).contains("color=\"#c49425\"");
            assertThat(fxml).doesNotContain("color=\"#f0b429\"");
            assertThat(fxml).contains("color=\"#8a6018\"");
            assertThat(fxml).contains("legendLens");
            assertThat(fxml).doesNotContain("fill=\"#f2c94c\"");
            assertThat(fxml).contains("legendCompare");
            assertThat(fxml).doesNotContain("width=\"6\" height=\"10\" fill=\"#8aaa50\"");
            assertThat(fxml).doesNotContain("width=\"6\" height=\"10\" fill=\"#c07850\"");
            assertThat(fxml).doesNotContain("width=\"6\" height=\"10\" fill=\"#d4b06a\"");
            assertThat(fxml).contains("legendPlayer");
            assertThat(fxml).contains("color=\"#f5c14a\"");
            assertThat(fxml).contains("color=\"#8a6418\"");
            assertThat(fxml).contains("color=\"#e88868\"");
            assertThat(fxml).contains("color=\"#8a3828\"");
            assertThat(fxml).contains("color=\"#e8a060\"");
            assertThat(fxml).contains("color=\"#8a5020\"");
            assertThat(fxml).contains("color=\"#b8a058\"");
            assertThat(fxml).contains("color=\"#6a5420\"");
            assertThat(fxml).doesNotContain("fill=\"#f5c14a\"");
            assertThat(fxml).doesNotContain("fill=\"#e88868\"");
            assertThat(fxml).doesNotContain("fill=\"#e8a060\"");
            assertThat(fxml).doesNotContain("fill=\"#b8a058\"");
            assertThat(fxml).contains("legendGhost");
            assertThat(fxml).contains("color=\"#e8e0d4\"");
            assertThat(fxml).contains("color=\"#6a6258\"");
            assertThat(fxml).doesNotContain("fill=\"#e8e0d4\"");
            assertThat(fxml).doesNotContain("fill=\"#8fb8ff\"");
            assertThat(fxml).contains("color=\"#19140f\"")
                    .doesNotContain("stroke=\"#2a2218\"");
            assertThat(fxml).contains("color=\"#0c0908\"")
                    .contains("stroke=\"rgba(242,234,216,0.28)\"");
        }
        assertThat(com.daedalus.desktop.ui.themes.CosmicTheme.PASSAGE_INK).isEqualTo("#484339");
        assertThat(com.daedalus.desktop.ui.themes.CosmicTheme.WALL_INK).isEqualTo("#19140f");
        assertThat(com.daedalus.desktop.ui.themes.CosmicTheme.BACKGROUND_INK).isEqualTo("#0c0908");
        assertThat(com.daedalus.desktop.ui.themes.CosmicTheme.VISITED_INK).isEqualTo("#3a3024");
        assertThat(Integer.parseInt(com.daedalus.desktop.ui.themes.CosmicTheme.VISITED_INK.substring(1, 3), 16))
                .isGreaterThan(Integer.parseInt(
                        com.daedalus.desktop.ui.themes.CosmicTheme.VISITED_INK.substring(5, 7), 16));
        assertThat(com.daedalus.desktop.ui.themes.CosmicTheme.FRONTIER_INK).isEqualTo("#d4a04c");
        assertThat(Integer.parseInt(com.daedalus.desktop.ui.themes.CosmicTheme.FRONTIER_INK.substring(1, 3), 16))
                .isGreaterThan(Integer.parseInt(
                        com.daedalus.desktop.ui.themes.CosmicTheme.FRONTIER_INK.substring(5, 7), 16));
    }

    @Test
    void fallsBackToFirstTheme_whenNamedDefaultMissing() {
        Theme noir   = fakeTheme("noir");
        Theme cosmic = fakeTheme("cosmic");

        ThemeManager mgr = new ThemeManager(List.of(noir, cosmic), "synthwave-not-installed");

        assertThat(mgr.active()).isSameAs(noir);
    }

    @Test
    void activeIsNull_whenNoThemesRegistered() {
        ThemeManager mgr = new ThemeManager(List.of(), "cosmic");

        assertThat(mgr.active()).isNull();
        assertThat(mgr.all()).isEmpty();
        assertThat(mgr.byId("cosmic")).isNull();
    }

    @Test
    void fogBackdropUsesTheWellVoidPocket() throws Exception {
        String src = java.nio.file.Files.readString(java.nio.file.Path.of(
                "src/main/java/com/daedalus/desktop/ui/MainController.java"));
        assertThat(src).contains("paintWellVoid(g, w, h);")
                .doesNotContain("g.setFill(Color.web(DesktopPaint.FOG_UNSEEN));");
    }

    @Test
    void leftoverEvenChromeFallsOffTowardFloorDim() throws Exception {
        String src = java.nio.file.Files.readString(java.nio.file.Path.of(
                "src/main/java/com/daedalus/desktop/ui/MainController.java"));
        assertThat(src).contains("Color.rgb(153, 111, 49, lip)")
                .contains("Color.rgb(153, 111, 49, chip)")
                .doesNotContain("Color.rgb(184, 133, 56, lip)")
                .doesNotContain("Color.rgb(184, 133, 56, chip)");
        try (var in = ThemeManagerTest.class.getResourceAsStream("/ui/cosmic.css")) {
            assertThat(in).as("cosmic.css is on the classpath").isNotNull();
            String css = new String(in.readAllBytes());
            assertThat(css)
                    .as("toolbar / status / export / canvas gold fall off toward floor-dim")
                    .contains("transparent transparent rgba(153, 111, 49, 0.45) transparent")
                    .contains(".toolbar .separator .line {\n    -fx-border-color: rgba(153, 111, 49, 0.28);")
                    .contains("-fx-border-color: rgba(153, 111, 49, 0.55)")
                    .contains("rgba(153, 111, 49, 0.45) transparent transparent transparent")
                    .contains(".exports .button:hover {\n    -fx-background-color: #1a1610;\n    -fx-border-color: rgba(153, 111, 49, 0.85);")
                    .as("KEEP leftover even field gold stays")
                    .contains("-fx-border-color: rgba(184, 133, 56, 0.28);\n    -fx-border-radius: 6;")
                    .contains("-fx-border-color: rgba(184, 133, 56, 0.85);\n}")
                    .contains("-fx-border-color: rgba(184, 133, 56, 0.32);\n    -fx-border-radius: 7;")
                    .contains(".check-box .box {\n    -fx-background-color: #07090c;\n    -fx-border-color: rgba(184, 133, 56, 0.28);");
        }
    }

    @Test
    void leftoverEvenGoldChipsFallOffTowardFloorDim() throws Exception {
        try (var in = ThemeManagerTest.class.getResourceAsStream("/ui/main.fxml")) {
            assertThat(in).as("main.fxml is on the classpath").isNotNull();
            String fxml = new String(in.readAllBytes());
            assertThat(fxml)
                    .as("tour / hardest / waypoint / race-B chip gold fall off toward floor-dim")
                    .contains("fx:id=\"legendHardest\"")
                    .contains("color=\"#c6a441\"")
                    .contains("fx:id=\"legendTour\"")
                    .contains("color=\"#af9158\"")
                    .contains("fx:id=\"legendWaypoint\"")
                    .contains("fx:id=\"legendRace\"")
                    .contains("color=\"#c49425\"")
                    .doesNotContain("color=\"#d4b06a\"")
                    .doesNotContain("color=\"#f0b429\"")
                    .as("KEEP leftover even lens gold stays")
                    .contains("fx:id=\"legendLens\"")
                    .contains("color=\"#f2c94c\"");
        }
        String src = java.nio.file.Files.readString(java.nio.file.Path.of(
                "src/main/java/com/daedalus/desktop/ui/MainController.java"));
        assertThat(src)
                .contains("Color.web(\"#c6a441\")")
                .contains("Color.web(\"#af9158\")")
                .contains("walkTrailInk(DesktopPaint.HARDEST,")
                .contains("walkTrailInk(DesktopPaint.TOUR,")
                .doesNotContain("Color.web(DesktopPaint.HARDEST)")
                .doesNotContain("Color.web(DesktopPaint.TOUR)");
    }

    private static Theme fakeTheme(String id) {
        return new Theme() {
            @Override public String id()             { return id; }
            @Override public String displayName()    { return id; }
            @Override public String stylesheetPath() { return "/ui/" + id + ".css"; }
            @Override public Color  passage()        { return Color.WHITE; }
            @Override public Color  wall()           { return Color.BLACK; }
            @Override public Color  start()          { return Color.GREEN; }
            @Override public Color  goal()           { return Color.RED; }
            @Override public Color  path()           { return Color.YELLOW; }
            @Override public Color  visited()        { return Color.GRAY; }
            @Override public Color  frontier()       { return Color.BLUE; }
            @Override public Color  player()         { return Color.MAGENTA; }
            @Override public Color  background()     { return Color.DARKGRAY; }
            @Override public Color  accent()         { return Color.CYAN; }
        };
    }
}
