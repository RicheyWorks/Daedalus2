// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.desktop.ui.themes.Theme;
import javafx.scene.Scene;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Theme registry + applier. The {@link Theme} list is auto-injected, so any theme
 * registered as a Spring bean — built-in or plugin-contributed — shows up here for free.
 */
@Component
public class ThemeManager {

    private final Map<String, Theme> themes = new ConcurrentHashMap<>();
    private final String defaultId;
    private Theme active;

    public ThemeManager(List<Theme> all,
                        @Value("${daedalus.ui.theme:cosmic}") String defaultId) {
        for (Theme t : all) themes.put(t.id(), t);
        this.defaultId = defaultId;
        this.active = themes.getOrDefault(defaultId, all.isEmpty() ? null : all.get(0));
    }

    public Collection<Theme> all() { return Collections.unmodifiableCollection(themes.values()); }

    public Theme byId(String id) { return themes.get(id); }

    public Theme active() { return active; }

    public void apply(Scene scene, String id) {
        Theme t = themes.get(id);
        if (t == null) return;
        this.active = t;
        scene.getStylesheets().clear();
        var url = getClass().getResource(t.stylesheetPath());
        if (url != null) scene.getStylesheets().add(url.toExternalForm());
    }

    public void applyDefault(Scene scene) {
        apply(scene, defaultId);
    }
}
