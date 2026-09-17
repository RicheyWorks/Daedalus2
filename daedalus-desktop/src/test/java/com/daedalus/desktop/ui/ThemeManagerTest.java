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
            assertThat(css).contains("rgba(184, 133, 56, 0.45)");
            assertThat(css).contains("dropshadow(one-pass-box, rgba(62, 224, 143, 0.28)");
            assertThat(css).contains("dropshadow(one-pass-box, rgba(184, 133, 56, 0.22)");
            assertThat(css).contains("-fx-border-color: rgba(184, 133, 56, 0.85)");
            assertThat(css).contains("-fx-border-color: rgba(184, 133, 56, 0.28)");
            assertThat(css).contains("-fx-border-color: rgba(184, 133, 56, 0.32)");
            assertThat(css).contains("-fx-border-color: rgba(184, 133, 56, 0.36)");
            assertThat(css).contains(".status-bar");
            assertThat(css)
                    .as("desktop well wears the same inset void shade as web #stage")
                    .contains("innershadow(gaussian, rgba(0, 0, 0, 0.35), 48");
            assertThat(css).contains("#16120e");
            assertThat(css).contains("#0c0908");
            assertThat(css).contains("-fx-background-color: #0c0908");
            assertThat(css).contains(".toolbar");
            assertThat(css).contains(".toolbar .brand");
            assertThat(css).contains("-fx-text-fill: #f2ead8");
            assertThat(css).contains(".status-bar");
            assertThat(css).contains(".status-bar .label");
            assertThat(css).contains("-fx-background-color: #16120e");
            assertThat(css).contains("rgba(16, 11, 8, 0.55)");
            assertThat(css).contains("rgba(16, 11, 8, 0.92)");
            assertThat(css).contains(".legend .label");
            assertThat(css).contains("#b09a72");
            assertThat(css).contains(".exports .button");
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
            assertThat(fxml).contains("fill=\"#484339\" stroke=\"rgba(242,234,216,0.28)\"");
            assertThat(fxml).contains("legendStart");
            assertThat(fxml).contains("fill=\"#484339\"");
            assertThat(fxml).contains("fill=\"#19140f\"");
            assertThat(fxml).contains("fill=\"#0c0908\"");
            assertThat(fxml).contains("fill=\"#c07850\"");
            assertThat(fxml).contains("fill=\"#c8a878\"");
            assertThat(fxml).contains("fill=\"#8aaa50\"");
            assertThat(fxml).contains("legendDeadend");
            assertThat(fxml).contains("legendTour");
            assertThat(fxml).contains("fill=\"#d4b06a\"");
            assertThat(fxml).contains("legendPath");
            assertThat(fxml).contains("fill=\"#8fb8ff\" arcWidth=\"3\" arcHeight=\"3\"");
            assertThat(fxml).contains("legendRace");
            assertThat(fxml).contains("legendLens");
            assertThat(fxml).contains("legendCompare");
            assertThat(fxml).contains("fill=\"#82b1ff\"");
            assertThat(fxml).contains("stroke=\"#2a2218\"");
        }
        assertThat(com.daedalus.desktop.ui.themes.CosmicTheme.PASSAGE_INK).isEqualTo("#484339");
        assertThat(com.daedalus.desktop.ui.themes.CosmicTheme.WALL_INK).isEqualTo("#19140f");
        assertThat(com.daedalus.desktop.ui.themes.CosmicTheme.BACKGROUND_INK).isEqualTo("#0c0908");
        assertThat(com.daedalus.desktop.ui.themes.CosmicTheme.VISITED_INK).isEqualTo("#3a3024");
        assertThat(Integer.parseInt(com.daedalus.desktop.ui.themes.CosmicTheme.VISITED_INK.substring(1, 3), 16))
                .isGreaterThan(Integer.parseInt(
                        com.daedalus.desktop.ui.themes.CosmicTheme.VISITED_INK.substring(5, 7), 16));
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
