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
