// SPDX-License-Identifier: MIT

package com.daedalus.desktop;

import com.daedalus.desktop.ui.ThemeManager;
import javafx.application.Application;
import javafx.fxml.FXMLLoader;
import javafx.scene.Parent;
import javafx.scene.Scene;
import javafx.stage.Stage;
import org.springframework.context.ConfigurableApplicationContext;

import java.net.URL;
import java.util.Objects;

/**
 * Primary stage. JavaFX instantiates this via {@link Application#launch}.
 * Pulls beans from the Spring context that {@link DaedalusLauncher} already booted.
 */
public class DaedalusPrimaryStage extends Application {

    private static final double DEFAULT_WIDTH = 1280.0;
    private static final double DEFAULT_HEIGHT = 800.0;

    private ConfigurableApplicationContext spring;
    private ThemeManager themeManager;

    @Override
    public void init() {
        this.spring = DaedalusLauncher.springContext();
        this.themeManager = spring.getBean(ThemeManager.class);
    }

    @Override
    public void start(Stage stage) throws Exception {
        URL fxml = Objects.requireNonNull(
                getClass().getResource("/ui/main.fxml"),
                "main.fxml missing from /resources/ui");

        FXMLLoader loader = new FXMLLoader(fxml);
        // Hand the controller a Spring-aware factory so @Autowired works in FXML controllers.
        loader.setControllerFactory(spring::getBean);

        Parent root = loader.load();
        Scene scene = new Scene(root, DEFAULT_WIDTH, DEFAULT_HEIGHT);

        themeManager.applyDefault(scene);

        stage.setTitle("Daedalus");
        stage.setScene(scene);
        stage.setMinWidth(960);
        stage.setMinHeight(640);
        stage.setOnCloseRequest(e -> DaedalusLauncher.shutdown());
        stage.show();
    }

    @Override
    public void stop() {
        DaedalusLauncher.shutdown();
    }
}
