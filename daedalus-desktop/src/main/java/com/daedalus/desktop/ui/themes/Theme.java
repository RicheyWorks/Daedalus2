// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui.themes;

import javafx.scene.paint.Color;

/**
 * A theme bundles a CSS stylesheet path with explicit color tokens used by the canvas
 * renderer (which can't pull values out of CSS the way controls can).
 *
 * <p>Themes are pluggable: external plugins can register their own by adding a
 * {@code Theme} bean and a CSS file in their JAR.
 */
public interface Theme {

    String id();
    String displayName();
    String stylesheetPath();   // classpath path, e.g. "/ui/cosmic.css"

    Color passage();
    Color wall();
    Color start();
    Color goal();
    Color path();
    Color visited();
    Color frontier();
    Color player();
    Color background();
    Color accent();
}
