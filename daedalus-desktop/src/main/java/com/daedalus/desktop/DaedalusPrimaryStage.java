// SPDX-License-Identifier: MIT

package com.daedalus.desktop;

import com.daedalus.desktop.ui.DesktopPaint;
import com.daedalus.desktop.ui.ThemeManager;
import javafx.application.Application;
import javafx.fxml.FXMLLoader;
import javafx.scene.Group;
import javafx.scene.Parent;
import javafx.scene.Scene;
import javafx.scene.image.PixelFormat;
import javafx.scene.image.WritableImage;
import javafx.scene.layout.StackPane;
import javafx.scene.paint.Color;
import javafx.scene.paint.CycleMethod;
import javafx.scene.paint.RadialGradient;
import javafx.scene.paint.Stop;
import javafx.scene.shape.Circle;
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
        StackPane shell = new StackPane();
        shell.getChildren().addAll(pageWash(shell), root);
        Scene scene = new Scene(shell, DEFAULT_WIDTH, DEFAULT_HEIGHT,
                Color.web(DesktopPaint.SCENE_FILL));

        themeManager.applyDefault(scene);

        WritableImage icon = new WritableImage(DesktopPaint.STAGE_ICON_SIZE,
                DesktopPaint.STAGE_ICON_SIZE);
        icon.getPixelWriter().setPixels(0, 0, DesktopPaint.STAGE_ICON_SIZE,
                DesktopPaint.STAGE_ICON_SIZE, PixelFormat.getIntArgbInstance(),
                DesktopPaint.stageIconPixels(), 0, DesktopPaint.STAGE_ICON_SIZE);
        stage.getIcons().setAll(icon);
        stage.setTitle("DAEDALUS");
        stage.setScene(scene);
        stage.setMinWidth(960);
        stage.setMinHeight(640);
        stage.setOnCloseRequest(e -> DaedalusLauncher.shutdown());
        stage.show();
    }

    /** Warm cap — same 1200px by 700px radii as the well {@code body} wash. */
    private static Group pageWash(StackPane shell) {
        Circle cap = new Circle(0, 0, DesktopPaint.pageWashRadiusX());
        cap.setScaleY(DesktopPaint.pageWashScaleY());
        cap.setMouseTransparent(true);
        cap.setFill(new RadialGradient(0, 0, 0, 0, DesktopPaint.pageWashRadiusX(), false,
                CycleMethod.NO_CYCLE,
                new Stop(0, Color.web("#16120e")),
                new Stop(DesktopPaint.PAGE_WASH_END, Color.web(DesktopPaint.SCENE_FILL)),
                new Stop(1, Color.web(DesktopPaint.SCENE_FILL))));
        Group layer = new Group(cap);
        layer.setMouseTransparent(true);
        layer.setManaged(false);
        layer.layoutXProperty().bind(javafx.beans.binding.Bindings.createDoubleBinding(
                () -> DesktopPaint.pageWashCenterX(shell.getWidth()), shell.widthProperty()));
        layer.layoutYProperty().bind(javafx.beans.binding.Bindings.createDoubleBinding(
                () -> DesktopPaint.pageWashCenterY(shell.getHeight()), shell.heightProperty()));
        return layer;
    }

    @Override
    public void stop() {
        DaedalusLauncher.shutdown();
    }
}
