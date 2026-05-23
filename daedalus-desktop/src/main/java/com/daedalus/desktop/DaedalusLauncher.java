// SPDX-License-Identifier: MIT

package com.daedalus.desktop;

import com.daedalus.server.DaedalusApp;
import javafx.application.Application;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;

/**
 * JavaFX entry point. Boots the Spring context first (so beans are wired before any UI work),
 * then launches the JavaFX runtime which constructs {@link DaedalusPrimaryStage}.
 *
 * <p>Run this for the desktop client. Run {@link DaedalusApp} for headless server-only mode.
 */
public class DaedalusLauncher {

    private static ConfigurableApplicationContext springContext;

    public static void main(String[] args) {
        // Boot Spring headlessly — JavaFX owns the Application lifecycle, not Spring.
        springContext = new SpringApplicationBuilder(DaedalusApp.class)
                .headless(false)
                .run(args);

        // Hand off to JavaFX. The stage class will pull beans from springContext.
        Application.launch(DaedalusPrimaryStage.class, args);
    }

    public static ConfigurableApplicationContext springContext() {
        return springContext;
    }

    public static void shutdown() {
        if (springContext != null) {
            springContext.close();
        }
    }
}
