// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui.themes;

import javafx.scene.paint.Color;
import org.springframework.stereotype.Component;

/**
 * Default visual theme. Same void / floor / mint / coral tokens as the web
 * painter — paired with {@code /ui/cosmic.css} so the canvas (which reads
 * tokens off {@link Theme}) and the JavaFX chrome (which reads CSS) are one
 * product. The old navy / neon pair made a dungeon look like a different game.
 *
 * <p>Registered as a Spring {@code @Component} so {@link com.daedalus.desktop.ui.ThemeManager}
 * picks it up via constructor injection of {@code List<Theme>}. The id matches the
 * {@code daedalus.ui.theme} default in {@code application.yml} ({@code "cosmic"}).
 */
@Component
public class CosmicTheme implements Theme {

    @Override public String id()              { return "cosmic"; }
    @Override public String displayName()     { return "Cosmic"; }
    @Override public String stylesheetPath()  { return "/ui/cosmic.css"; }

    @Override public Color background()       { return Color.web("#07090c"); }
    @Override public Color wall()             { return Color.web("#0b0f14"); }
    @Override public Color passage()          { return Color.web("#3d4a58"); }
    @Override public Color start()            { return Color.web("#3ee08f"); }
    @Override public Color goal()             { return Color.web("#ff5a5f"); }
    @Override public Color path()             { return Color.web("#8fb8ff"); }
    @Override public Color visited()          { return Color.web("#2a3440"); }
    @Override public Color frontier()         { return Color.web("#7eb6ff"); }
    @Override public Color player()           { return Color.web("#f5c14a"); }
    @Override public Color accent()           { return Color.web("#3ee08f"); }
}
