// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui.themes;

import javafx.scene.paint.Color;
import org.springframework.stereotype.Component;

/**
 * Default visual theme. Dark navy backgrounds with cyan and magenta accents — paired with
 * {@code /ui/cosmic.css} so the canvas tokens (read off {@link Theme} by the renderer)
 * harmonize with the JavaFX control styling (read off CSS by the platform).
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

    @Override public Color background()       { return Color.web("#0a0e27"); }
    @Override public Color wall()             { return Color.web("#1d2456"); }
    @Override public Color passage()          { return Color.web("#c0d0ff"); }
    @Override public Color start()            { return Color.web("#00ff88"); }
    @Override public Color goal()             { return Color.web("#ff3388"); }
    @Override public Color path()             { return Color.web("#ffd700"); }
    @Override public Color visited()          { return Color.web("#3d4a99"); }
    @Override public Color frontier()         { return Color.web("#5a6cb8"); }
    @Override public Color player()           { return Color.web("#ffaa00"); }
    @Override public Color accent()           { return Color.web("#5a8cff"); }
}
