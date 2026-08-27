// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.desktop.ui.themes.Theme;
import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;
import com.daedalus.model.TileType;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.MazeSolverService;
import javafx.animation.AnimationTimer;
import javafx.concurrent.Task;
import com.daedalus.solver.MazeSolver;
import com.daedalus.solver.solvers.SolverRegistry;
import javafx.fxml.FXML;
import javafx.scene.canvas.Canvas;
import javafx.scene.canvas.GraphicsContext;
import javafx.scene.control.Button;
import javafx.scene.control.CheckBox;
import javafx.scene.control.ComboBox;
import javafx.scene.control.Label;
import javafx.scene.control.Spinner;
import javafx.scene.control.SpinnerValueFactory;
import javafx.scene.control.TextField;
import javafx.scene.input.KeyCode;
import javafx.scene.input.KeyEvent;
import javafx.scene.input.MouseEvent;
import javafx.scene.layout.HBox;
import javafx.scene.layout.Pane;
import javafx.scene.image.PixelFormat;
import javafx.scene.image.WritableImage;
import javafx.scene.paint.Color;
import javafx.scene.text.Font;
import javafx.scene.text.FontWeight;
import javafx.scene.text.TextAlignment;
import javafx.scene.transform.Scale;
import javafx.stage.FileChooser;
import javafx.stage.Window;
import org.springframework.stereotype.Component;

import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

import javax.imageio.ImageIO;

/**
 * Controller for {@code /ui/main.fxml}.
 *
 * <p>Wired into the FXML loader via Spring's controller factory in
 * {@code DaedalusPrimaryStage}, so this class can constructor-inject any bean —
 * {@link GeneratorRegistry}, {@link SolverRegistry}, {@link DesktopWork},
 * {@link ThemeManager}.
 *
 * <p>Responsibilities:
 * <ul>
 *   <li>Populate generator / solver dropdowns from the live registries (built-ins + plugins).</li>
 *   <li>Run a generation on Generate — delegates through {@link DesktopWork} so plugin
 *       events and metrics fire exactly the same way as the REST surface.</li>
 *   <li>Run a solve on Solve — same delegation rationale; overlays the returned path on
 *       the canvas in the theme's {@code path()} color.</li>
 *   <li>Track a movable player marker; arrow keys / WASD or a click walk it through
 *       open walls, reaching the goal flips the status bar to a celebration message.
 *       Fog paints only stood-on memory and touching walls, same as the web dungeon.</li>
 *   <li>Render everything on a {@link Canvas}, repaint on resize. Layout,
 *       path tiles, and the player disc live on {@link DesktopPaint}.</li>
 * </ul>
 *
 * <p>JavaFX threading: every {@code @FXML} method runs on the JavaFX Application Thread, which
 * is also the thread that mutates the Canvas. This class used to run generation and solve
 * inline there, on the documented assumption that both were "fast enough at the Spinner-bounded
 * sizes (≤ 128² = 16 384 cells)", with an explicit instruction to wrap them in a
 * {@link javafx.concurrent.Task} if that ever reached the multi-second range.
 *
 * <p>It did. Re-measured at the spinner's own maximum: hunt-and-kill generates a 128×128 in
 * <b>1101 ms</b>, and IDA* spends its node budget and refuses after <b>1783 ms</b> on a perfect
 * 128×128 and 1518 ms on a dungeon. Frozen window, no repaint, no input, for all of it. So both
 * now run on a {@link javafx.concurrent.Task} via {@link DesktopWork}, the controls disable
 * while one is in flight, and the status label reports the outcome when it lands. Canvas
 * mutation stays on the FX thread, where it belongs.
 */
@Component
public class MainController {

    /** Maximum row / col spinner value; matches REST validation cap and keeps the canvas legible. */
    private static final int MAX_DIM = 128;

    private final GeneratorRegistry generatorRegistry;
    private final SolverRegistry solverRegistry;
    private final DesktopWork work;
    private final ThemeManager themeManager;

    @FXML private ComboBox<String> generatorChoice;
    @FXML private Spinner<Integer> rowsSpinner;
    @FXML private Spinner<Integer> colsSpinner;
    @FXML private Spinner<Integer> hotspotSpinner;
    @FXML private Spinner<Integer> hotspotCostSpinner;
    @FXML private ComboBox<Double> braidChoice;
    @FXML private TextField seedField;
    @FXML private Button generateButton;     // referenced from FXML, kept for future enable/disable
    @FXML private ComboBox<String> solverChoice;
    @FXML private Button solveButton;        // ditto
    @FXML private Button resetButton;        // ditto
    @FXML private CheckBox fogToggle;
    @FXML private CheckBox heatToggle;
    @FXML private CheckBox cutsToggle;
    @FXML private HBox exportBox;
    @FXML private Pane canvasParent;
    @FXML private Canvas canvas;
    @FXML private HBox legendBox;
    @FXML private Label legendStart;
    @FXML private Label legendGoal;
    @FXML private Label legendPath;
    @FXML private Label legendPlayer;
    @FXML private Label legendHotspot;
    @FXML private Label legendFog;
    @FXML private Label legendChoke;
    @FXML private Label statusLabel;

    /** Last successfully-generated maze; held so resize events can re-render it. */
    private MazeGenerationService.Cached current;

    /** Solver path overlay (cell-coordinate {@link Point}s) — null when no solve has run since the last Generate. */
    private List<Point> currentPath;

    /** Full solve route; {@link #currentPath} is the visible prefix while it unfolds. */
    private List<Point> solvedPath;

    private AnimationTimer pathReveal;

    /** Player marker position. Set on Generate / Reset; updated on arrow-key moves. */
    private Point playerPos;

    /** Stood-on cells for the walk wash — web paints {@code trails}; a lone disc left no corridor. */
    private final List<Point> playerWalk = new ArrayList<>();

    /** Cached: true once playerPos has reached current.metadata().goal(). Reset on Generate / Reset. */
    private boolean reachedGoal;

    /** Goal-sourced distance field — cleared on Generate and Fog. */
    private DesktopPaint.Field currentField;

    /** Min-cut passages — cleared on Generate and Fog. */
    private DesktopPaint.Cuts currentCuts;

    public MainController(GeneratorRegistry generatorRegistry,
                          SolverRegistry solverRegistry,
                          DesktopWork work,
                          ThemeManager themeManager) {
        this.generatorRegistry = generatorRegistry;
        this.solverRegistry = solverRegistry;
        this.work = work;
        this.themeManager = themeManager;
    }

    /**
     * Called by the FXML loader after all {@code @FXML}-annotated fields have been wired.
     * Populates choices, sets spinner ranges, binds the canvas to its parent's size, arms
     * a redraw on resize, and installs the keyboard handler for player movement.
     */
    @FXML
    public void initialize() {
        // Generator choices — sorted so the dropdown order is stable across runs.
        List<String> genIds = generatorRegistry.all().stream()
                .map(MazeGenerator::id)
                .sorted(Comparator.naturalOrder())
                .toList();
        generatorChoice.getItems().setAll(genIds);
        if (!genIds.isEmpty()) {
            // Default to recursive-backtracker if registered (textbook starter, recognisable
            // "river" texture); otherwise pick the first id.
            String preferred = genIds.contains("recursive-backtracker") ? "recursive-backtracker" : genIds.get(0);
            generatorChoice.getSelectionModel().select(preferred);
        }

        // Solver choices — same pattern.
        List<String> solverIds = solverRegistry.all().stream()
                .map(MazeSolver::id)
                .sorted(Comparator.naturalOrder())
                .toList();
        solverChoice.getItems().setAll(solverIds);
        if (!solverIds.isEmpty()) {
            String preferred = solverIds.contains("a-star")
                    ? "a-star"
                    : solverIds.contains("astar") ? "astar" : solverIds.get(0);
            solverChoice.getSelectionModel().select(preferred);
        }

        rowsSpinner.setValueFactory(new SpinnerValueFactory.IntegerSpinnerValueFactory(2, MAX_DIM, 21));
        colsSpinner.setValueFactory(new SpinnerValueFactory.IntegerSpinnerValueFactory(2, MAX_DIM, 31));
        if (braidChoice != null) {
            braidChoice.getItems().setAll(0.0, 0.4, 0.8);
            braidChoice.getSelectionModel().select(0.0);
        }
        if (hotspotSpinner != null) {
            hotspotSpinner.setValueFactory(
                    new SpinnerValueFactory.IntegerSpinnerValueFactory(0, 64, 0));
        }
        if (hotspotCostSpinner != null) {
            hotspotCostSpinner.setValueFactory(
                    new SpinnerValueFactory.IntegerSpinnerValueFactory(1, 1000, 25));
        }

        // Backing store is the pane times the window output scale — a 2× display
        // used to smear thin walls the same way the web did before devicePixelRatio.
        canvasParent.widthProperty().addListener((obs, oldV, newV) -> resizeBacking());
        canvasParent.heightProperty().addListener((obs, oldV, newV) -> resizeBacking());
        canvas.sceneProperty().addListener((obs, oldS, scene) -> {
            if (scene == null) {
                return;
            }
            scene.windowProperty().addListener((wObs, oldW, win) -> armWindow(win));
            armWindow(scene.getWindow());
        });

        // Keyboard handler for player movement. Canvas grabs focus on Generate so arrow
        // keys "just work" without an explicit click. Pressing a movement key while a text
        // field is focused (e.g. typing in Seed) goes to the text field; that's the right
        // behavior — explicit click on the maze area transfers focus back.
        canvas.setFocusTraversable(true);
        canvas.setOnMouseClicked(this::onCanvasClicked);
        canvas.setOnKeyPressed(this::onKeyPressed);

        if (legendBox != null) {
            legendBox.layoutXProperty().bind(
                    canvasParent.widthProperty().subtract(legendBox.widthProperty()).divide(2));
            legendBox.layoutYProperty().bind(
                    canvasParent.heightProperty().subtract(legendBox.heightProperty()).subtract(4));
        }
        if (exportBox != null) {
            exportBox.layoutXProperty().bind(
                    canvasParent.widthProperty().subtract(exportBox.widthProperty()).subtract(10));
            exportBox.layoutYProperty().set(8);
        }
        syncLegend();
    }

    /** Wired from the FXML's Generate button. */
    @FXML
    public void onGenerate() {
        String genId = generatorChoice.getValue();
        if (genId == null || genId.isBlank()) {
            statusLabel.setText("Pick a generator first.");
            return;
        }
        int rows = rowsSpinner.getValue();
        int cols = colsSpinner.getValue();

        long seed;
        String seedText = seedField.getText();
        if (seedText == null || seedText.isBlank()) {
            seed = System.nanoTime();
        } else {
            try {
                seed = Long.parseLong(seedText.trim());
            } catch (NumberFormatException e) {
                statusLabel.setText("Seed must be a long integer (or empty for random); got: " + seedText);
                return;
            }
        }

        int spotCount = hotspotSpinner != null ? hotspotSpinner.getValue() : 0;
        int spotCost = hotspotCostSpinner != null ? hotspotCostSpinner.getValue() : 25;
        var spots = DesktopPaint.placeSpots(rows, cols, spotCount, seed, spotCost);
        double braid = braidChoice != null && braidChoice.getValue() != null
                ? braidChoice.getValue() : 0.0;

        long t0 = System.nanoTime();
        Task<MazeGenerationService.Cached> task = new Task<>() {
            @Override
            protected MazeGenerationService.Cached call() throws Exception {
                return work.generateJob(genId, rows, cols, seed, spots, braid).call();
            }
        };
        task.setOnSucceeded(e -> {
            current = task.getValue();
            long elapsedMs = (System.nanoTime() - t0) / 1_000_000L;

            // Fresh maze invalidates any prior solve overlay and snaps the player to start.
            stopPathReveal();
            currentPath = null;
            solvedPath = null;
            playerPos = current.metadata().start();
            resetWalk(playerPos);
            reachedGoal = false;
            clearTheory();

            redraw();
            canvas.requestFocus();

            String actualId = current.metadata().generatorId();
            String genNote = actualId.equals(genId) ? "" : "  (fell back from " + genId + ")";
            String braidNote = current.braid() != null ? ", braid=" + current.braid() : "";
            statusLabel.setText(String.format(
                    "Drew %d×%d via %s, seed=%d%s, %dms%s — arrows / WASD or a click to walk.",
                    rows, cols, actualId, seed, braidNote, elapsedMs, genNote));
            busy(false);
        });
        task.setOnFailed(e ->
                fail(DesktopWork.describeFailure("Generation", task.getException())));
        run(task, "Generating " + rows + "×" + cols + " via " + genId + "…");
    }

    /** Disable the controls, say what is happening, and run the job off the FX thread. */
    private void run(Task<?> task, String message) {
        busy(true);
        statusLabel.setText(message);
        Thread worker = new Thread(task, "daedalus-desktop-work");
        worker.setDaemon(true);   // never keep the JVM alive past window close
        worker.start();
    }

    private void fail(String message) {
        statusLabel.setText(message);
        busy(false);
    }

    /**
     * One job at a time. Without this, a second Generate while the first is still running would
     * race two workers to assign {@code current} and the later click could lose.
     */
    private void busy(boolean running) {
        generateButton.setDisable(running);
        solveButton.setDisable(running);
    }

    /** Wired from the FXML's Solve button. Runs the chosen solver against {@link #current}. */
    @FXML
    public void onSolve() {
        if (current == null) {
            statusLabel.setText("Generate a maze first, then click Solve.");
            return;
        }
        if (fogOn()) {
            statusLabel.setText("Fog hides the solver path — uncheck Fog to solve.");
            return;
        }
        String solverId = solverChoice.getValue();
        if (solverId == null || solverId.isBlank()) {
            statusLabel.setText("Pick a solver first.");
            return;
        }
        long t0 = System.nanoTime();
        var grid = current.grid();
        var mazeId = current.metadata().id();
        Task<MazeSolverService.Result> task = new Task<>() {
            @Override
            protected MazeSolverService.Result call() throws Exception {
                return work.solveJob(solverId, grid, mazeId).call();
            }
        };
        task.setOnSucceeded(e -> {
            long elapsedMs = (System.nanoTime() - t0) / 1_000_000L;
            solvedPath = task.getValue().path();
            currentPath = DesktopPaint.pathPrefix(solvedPath, 0.01);
            startPathReveal();
            canvas.requestFocus();
            statusLabel.setText(String.format(
                    "Solved with %s in %dms — %d cells on the path.",
                    solverId, elapsedMs, solvedPath == null ? 0 : solvedPath.size()));
            busy(false);
        });
        task.setOnFailed(e -> fail(DesktopWork.describeFailure("Solve", task.getException())));
        run(task, "Solving with " + solverId + "…");
    }

    /** Wired from the FXML's Reset button. Snaps the player back to the start cell. */
    @FXML
    public void onReset() {
        if (current == null) return;
        playerPos = current.metadata().start();
        resetWalk(playerPos);
        reachedGoal = false;
        redraw();
        canvas.requestFocus();
        statusLabel.setText("Reset to start.");
    }

    /** Wired from the FXML Heat checkbox. Same goal-sourced field as the web heat map. */
    @FXML
    public void onHeat() {
        if (heatToggle == null || !heatToggle.isSelected()) {
            currentField = null;
            redraw();
            return;
        }
        if (current == null) {
            heatToggle.setSelected(false);
            statusLabel.setText("Generate a maze first, then check Heat.");
            return;
        }
        if (fogOn()) {
            heatToggle.setSelected(false);
            statusLabel.setText("Fog hides the distance field — uncheck Fog to heat.");
            return;
        }
        var grid = current.grid();
        Task<DesktopPaint.Field> task = new Task<>() {
            @Override
            protected DesktopPaint.Field call() throws Exception {
                return work.fieldJob(grid).call();
            }
        };
        task.setOnSucceeded(e -> {
            currentField = task.getValue();
            int farthest = currentField == null ? 0 : currentField.maxDistance();
            statusLabel.setText("Distance from the goal — farthest " + farthest + " steps.");
            redraw();
            canvas.requestFocus();
            busy(false);
        });
        task.setOnFailed(e -> {
            heatToggle.setSelected(false);
            fail(DesktopWork.describeFailure("Heat", task.getException()));
        });
        run(task, "Shading the distance field…");
    }

    private void clearField() {
        currentField = null;
        if (heatToggle != null) {
            heatToggle.setSelected(false);
        }
    }

    private void clearTheory() {
        clearField();
        currentCuts = null;
        if (cutsToggle != null) {
            cutsToggle.setSelected(false);
        }
    }

    /** Wired from the FXML Cuts checkbox. Same min-cut overlay as the web Analyze button. */
    @FXML
    public void onCuts() {
        if (cutsToggle == null || !cutsToggle.isSelected()) {
            currentCuts = null;
            redraw();
            return;
        }
        if (current == null) {
            cutsToggle.setSelected(false);
            statusLabel.setText("Generate a maze first, then check Cuts.");
            return;
        }
        if (fogOn()) {
            cutsToggle.setSelected(false);
            statusLabel.setText("Fog hides the cuts — uncheck Fog to analyze.");
            return;
        }
        var grid = current.grid();
        Task<DesktopPaint.Cuts> task = new Task<>() {
            @Override
            protected DesktopPaint.Cuts call() throws Exception {
                return work.cutsJob(grid).call();
            }
        };
        task.setOnSucceeded(e -> {
            currentCuts = task.getValue();
            int n = currentCuts == null ? 0 : currentCuts.cutSize();
            int ends = currentCuts == null || currentCuts.deadEnds() == null
                    ? 0 : currentCuts.deadEnds().size();
            statusLabel.setText(n == 1
                    ? "1 chokepoint · " + ends + " dead ends."
                    : n + " chokepoints · " + ends + " dead ends.");
            redraw();
            canvas.requestFocus();
            busy(false);
        });
        task.setOnFailed(e -> {
            cutsToggle.setSelected(false);
            fail(DesktopWork.describeFailure("Cuts", task.getException()));
        });
        run(task, "Finding the min-cut…");
    }

    /** Snapshot the well — same picture the web PNG takes, at the backing-store resolution. */
    @FXML
    public void onExportPng() {
        if (current == null || canvas.getScene() == null) {
            return;
        }
        FileChooser chooser = new FileChooser();
        chooser.setTitle("Save maze");
        chooser.setInitialFileName("maze.png");
        chooser.getExtensionFilters().add(new FileChooser.ExtensionFilter("PNG", "*.png"));
        File file = chooser.showSaveDialog(canvas.getScene().getWindow());
        if (file == null) {
            return;
        }
        try {
            writePng(snapshotWell(), file);
            statusLabel.setText("Saved " + file.getName() + ".");
        } catch (IOException e) {
            statusLabel.setText("Could not save PNG: " + e.getMessage());
        }
        canvas.requestFocus();
    }

    private WritableImage snapshotWell() {
        int pw = (int) Math.round(canvas.getWidth());
        int ph = (int) Math.round(canvas.getHeight());
        var saved = List.copyOf(canvas.getTransforms());
        canvas.getTransforms().clear();
        WritableImage snap = new WritableImage(Math.max(1, pw), Math.max(1, ph));
        canvas.snapshot(null, snap);
        canvas.getTransforms().setAll(saved);
        return snap;
    }

    private static void writePng(WritableImage snap, File file) throws IOException {
        int w = (int) Math.round(snap.getWidth());
        int h = (int) Math.round(snap.getHeight());
        int[] buf = new int[w * h];
        snap.getPixelReader().getPixels(0, 0, w, h,
                PixelFormat.getIntArgbInstance(), buf, 0, w);
        BufferedImage out = new BufferedImage(w, h, BufferedImage.TYPE_INT_ARGB);
        out.setRGB(0, 0, w, h, buf, 0, w);
        if (!ImageIO.write(out, "png", file)) {
            throw new IOException("PNG writer is not available");
        }
    }

    /** Wired from the FXML Fog checkbox. Checking it starts a fresh walk. */
    @FXML
    public void onFog() {
        if (fogOn()) {
            playerPos = current.metadata().start();
            resetWalk(playerPos);
            reachedGoal = false;
            stopPathReveal();
            currentPath = null;
            solvedPath = null;
            clearTheory();
            statusLabel.setText("Fog of war — arrows / WASD or a click walk the dungeon.");
        } else if (current != null) {
            statusLabel.setText("Fog lifted — the whole dungeon is visible.");
        }
        redraw();
        canvas.requestFocus();
    }

    // ---------- key handling ----------

    /**
     * Translate an arrow / WASD press into a {@link Direction} and try to move the player.
     * Other keys are ignored (the event isn't consumed, so e.g. Tab still navigates focus).
     */
    private void onKeyPressed(KeyEvent e) {
        Direction dir = directionForKey(e.getCode());
        if (dir == null) return;
        e.consume();
        tryMove(dir);
    }

    /**
     * Click an adjacent passage to step — same hit-test as {@code stage.js}.
     * A miss still focuses the canvas so arrows keep working.
     */
    private void onCanvasClicked(MouseEvent e) {
        canvas.requestFocus();
        if (current == null || playerPos == null) {
            return;
        }
        DesktopPaint.Backing store = backing();
        TileType[][] tiles = current.grid().toTileGrid();
        if (store == null || tiles.length == 0) {
            return;
        }
        DesktopPaint.Layout layout = DesktopPaint.Layout.fitMaze(
                tiles.length, tiles[0].length, store.cssW(), store.cssH());
        Point hit = DesktopPaint.hitCell(layout, store, e.getX(), e.getY());
        Direction dir = DesktopWalk.toward(playerPos, hit);
        if (dir != null) {
            tryMove(dir);
        }
    }

    private static Direction directionForKey(KeyCode code) {
        return switch (code) {
            case UP, W    -> Direction.NORTH;
            case DOWN, S  -> Direction.SOUTH;
            case LEFT, A  -> Direction.WEST;
            case RIGHT, D -> Direction.EAST;
            default       -> null;
        };
    }

    /**
     * Move the player one cell in {@code dir} if the wall between current and target is
     * carved. No-op if there's no maze, the player has already reached the goal, or the
     * wall is closed. Updates the status bar with a celebration when the goal is reached.
     */
    private void tryMove(Direction dir) {
        if (current == null) return;
        DesktopWalk.Outcome step = DesktopWalk.step(
                current.grid(), playerPos, current.metadata().goal(), dir, reachedGoal);
        if (!step.moved()) {
            return;
        }
        playerPos = step.position();
        rememberWalk(playerPos);
        if (step.reachedGoal()) {
            reachedGoal = true;
            statusLabel.setText("Reached the goal!  Press Reset, or Generate a new maze.");
        }
        redraw();
    }

    // ---------- rendering ----------

    private void stopPathReveal() {
        if (pathReveal != null) {
            pathReveal.stop();
            pathReveal = null;
        }
    }

    /** Unfold the route the way the web painter does — not a finished ribbon. */
    private void startPathReveal() {
        stopPathReveal();
        List<Point> full = solvedPath;
        if (full == null || full.isEmpty()) {
            currentPath = full;
            redraw();
            return;
        }
        long budgetNs = DesktopPaint.pathRevealMs(full.size()) * 1_000_000L;
        long started = System.nanoTime();
        pathReveal = new AnimationTimer() {
            @Override
            public void handle(long now) {
                double progress = (System.nanoTime() - started) / (double) budgetNs;
                currentPath = DesktopPaint.pathPrefix(full, progress);
                redraw();
                if (progress >= 1) {
                    currentPath = full;
                    stopPathReveal();
                }
            }
        };
        pathReveal.start();
    }

    private void armWindow(Window win) {
        if (win == null) {
            return;
        }
        win.outputScaleXProperty().addListener((obs, oldV, newV) -> resizeBacking());
        win.outputScaleYProperty().addListener((obs, oldV, newV) -> resizeBacking());
        resizeBacking();
    }

    private DesktopPaint.Backing backing() {
        double sx = 1;
        double sy = 1;
        if (canvas.getScene() != null && canvas.getScene().getWindow() != null) {
            Window win = canvas.getScene().getWindow();
            sx = win.getOutputScaleX();
            sy = win.getOutputScaleY();
        }
        return DesktopPaint.Backing.of(canvasParent.getWidth(), canvasParent.getHeight(), sx, sy);
    }

    private void resizeBacking() {
        DesktopPaint.Backing store = backing();
        if (store == null) {
            return;
        }
        if (Math.abs(canvas.getWidth() - store.pixelW()) > 0.5
                || Math.abs(canvas.getHeight() - store.pixelH()) > 0.5) {
            canvas.setWidth(store.pixelW());
            canvas.setHeight(store.pixelH());
        }
        canvas.getTransforms().setAll(new Scale(1 / store.scaleX(), 1 / store.scaleY(), 0, 0));
        redraw();
    }

    /**
     * Paint {@link #current} onto the canvas. Layered:
     * <ol>
     *   <li>Background fill.</li>
     *   <li>Tile grid via {@link MazeGrid#toTileGrid()} — walls and passages. Start and
     *       goal tiles paint as floor; the discs come later.</li>
     *   <li>Solve path overlay (if {@link #currentPath} is set) — drawn under the discs.</li>
     *   <li>Start / goal discs, then the player — last so it's always on top.</li>
     * </ol>
     * Thin-wall cells, centered with letterboxing on the longer axis so the maze isn't stretched.
     */
    private void redraw() {
        DesktopPaint.Backing store = backing();
        if (store == null) {
            return;
        }
        double w = store.cssW();
        double h = store.cssH();

        Theme theme = themeManager.active();
        GraphicsContext g = canvas.getGraphicsContext2D();
        g.setTransform(store.scaleX(), 0, 0, store.scaleY(), 0, 0);

        Color bg = fogOn()
                ? Color.web(DesktopPaint.FOG_UNSEEN)
                : (theme != null ? theme.wall() : Color.web("#0b0f14"));
        g.setFill(bg);
        g.fillRect(0, 0, w, h);

        if (current == null) {
            g.setFill(theme != null ? theme.wall() : Color.web("#0b0f14"));
            g.fillRect(0, 0, w, h);
            DesktopPaint.Layout mark = DesktopPaint.emptyMarkLayout(w, h);
            if (mark != null && theme != null) {
                g.setGlobalAlpha(0.38);
                g.setFill(theme.passage());
                for (DesktopPaint.TileRect tile : DesktopPaint.emptyMarkFloors()) {
                    g.fillRect(mark.x(tile.tileCol()), mark.y(tile.tileRow()),
                            mark.w(tile.tileCol()), mark.h(tile.tileRow()));
                }
                g.setGlobalAlpha(0.7);
                paintDisc(g, DesktopPaint.endpointMarker(mark, DesktopPaint.EMPTY_MARK_START),
                        theme.start());
                paintDisc(g, DesktopPaint.endpointMarker(mark, DesktopPaint.EMPTY_MARK_GOAL),
                        theme.goal());
                g.setGlobalAlpha(1);
            }
            g.setTextAlign(TextAlignment.CENTER);
            g.setFill(Color.web("#9aa3ad"));
            g.setFont(Font.font("Segoe UI", FontWeight.SEMI_BOLD, 12));
            g.fillText(DesktopPaint.EMPTY_WORDMARK, w / 2, h / 2 + 42);
            g.setFill(Color.web("#6b7580"));
            g.setFont(Font.font("Segoe UI", FontWeight.SEMI_BOLD, 13));
            g.fillText(DesktopPaint.EMPTY_TITLE, w / 2, h / 2 + 66);
            g.setFill(Color.web("#4a5560"));
            g.setFont(Font.font("Segoe UI", 13));
            g.fillText(DesktopPaint.EMPTY_DETAIL, w / 2, h / 2 + 86);
            g.fillText(DesktopPaint.EMPTY_HINT, w / 2, h / 2 + 104);
            syncLegend();
            return;
        }

        TileType[][] tiles = current.grid().toTileGrid();
        DesktopPaint.Layout layout = DesktopPaint.Layout.fitMaze(
                tiles.length, tiles[0].length, w, h);
        if (layout == null) return;

        DesktopPaint.Fog fog = fogScene();
        if (fog != null) {
            paintFogDungeon(g, layout, tiles, theme, fog);
            syncLegend();
            return;
        }

        // ---- 1) tile grid, then the web corridor highlight ----
        for (int r = 0; r < layout.tileRows(); r++) {
            for (int c = 0; c < layout.tileCols(); c++) {
                TileType role = DesktopPaint.floorRole(tiles[r][c]);
                g.setFill(colorFor(role, theme));
                g.fillRect(layout.x(c), layout.y(r), layout.w(c), layout.h(r));
                if (role != TileType.WALL) {
                    paintHairline(g, DesktopPaint.floorHiStroke(layout, r, c));
                }
            }
        }

        if (current.hotspots() != null && !current.hotspots().isEmpty()) {
            DesktopPaint.HotWash wash = DesktopPaint.hotspotWash(current.hotspots(), tiles);
            g.setFill(Color.web(DesktopPaint.HOTSPOT));
            for (var spot : wash.cells()) {
                g.setGlobalAlpha(DesktopPaint.hotspotCellAlpha(spot.cost()));
                int tr = 2 * spot.row() + 1;
                int tc = 2 * spot.col() + 1;
                g.fillRect(layout.x(tc), layout.y(tr), layout.w(tc), layout.h(tr));
            }
            g.setGlobalAlpha(DesktopPaint.HOTSPOT_OPENING_ALPHA);
            for (DesktopPaint.TileRect tile : wash.openings()) {
                g.fillRect(layout.x(tile.tileCol()), layout.y(tile.tileRow()),
                        layout.w(tile.tileCol()), layout.h(tile.tileRow()));
            }
            g.setGlobalAlpha(1);
        }

        if (currentField != null) {
            int max = currentField.maxDistance();
            int[][] dist = currentField.distances();
            for (int r = 0; r < dist.length; r++) {
                for (int c = 0; c < dist[r].length; c++) {
                    DesktopPaint.FieldTone tone = DesktopPaint.fieldCell(dist[r][c], max);
                    if (tone == null) {
                        continue;
                    }
                    g.setFill(Color.web(tone.color()));
                    g.setGlobalAlpha(tone.alpha());
                    g.fillRect(layout.x(2 * c + 1), layout.y(2 * r + 1),
                            layout.w(2 * c + 1), layout.h(2 * r + 1));
                }
            }
            g.setFill(Color.web(DesktopPaint.fieldOpeningColor()));
            g.setGlobalAlpha(DesktopPaint.FIELD_OPENING_ALPHA);
            for (DesktopPaint.TileRect tile : DesktopPaint.fieldOpenings(dist, tiles)) {
                g.fillRect(layout.x(tile.tileCol()), layout.y(tile.tileRow()),
                        layout.w(tile.tileCol()), layout.h(tile.tileRow()));
            }
            g.setGlobalAlpha(1);
        }

        // ---- 2) player walk, then solve-path overlay ----
        if (!playerWalk.isEmpty() && theme != null) {
            g.setGlobalAlpha(0.32);
            g.setFill(theme.player());
            for (DesktopPaint.TileRect tile : DesktopPaint.walkOverlay(playerWalk)) {
                g.fillRect(layout.x(tile.tileCol()), layout.y(tile.tileRow()),
                        layout.w(tile.tileCol()), layout.h(tile.tileRow()));
            }
            g.setGlobalAlpha(1);
        }
        if (currentPath != null && !currentPath.isEmpty() && theme != null) {
            g.setGlobalAlpha(DesktopPaint.PATH_ALPHA);
            g.setFill(theme.path());
            for (DesktopPaint.TileRect tile : DesktopPaint.pathOverlay(
                    currentPath, current.metadata().start(), current.metadata().goal())) {
                g.fillRect(layout.x(tile.tileCol()), layout.y(tile.tileRow()),
                        layout.w(tile.tileCol()), layout.h(tile.tileRow()));
            }
            g.setGlobalAlpha(1);
            paintDisc(g, DesktopPaint.pathHeadMarker(layout, currentPath), theme.path());
        }

        if (currentCuts != null) {
            g.setFill(Color.web(DesktopPaint.CHOKE));
            for (var passage : currentCuts.chokepoints()) {
                DesktopPaint.ChokeMark mark = DesktopPaint.chokeMark(layout, passage);
                if (mark == null) {
                    continue;
                }
                g.setGlobalAlpha(0.35);
                g.fillRect(mark.haloX(), mark.haloY(), mark.haloW(), mark.haloH());
                g.setGlobalAlpha(0.95);
                g.fillRect(mark.x(), mark.y(), mark.w(), mark.h());
            }
            g.setGlobalAlpha(1);
            for (Point end : currentCuts.deadEnds()) {
                paintDisc(g, DesktopPaint.deadEndMarker(layout, end),
                        Color.web(DesktopPaint.DEAD_END));
            }
        }

        // ---- 3) start / goal discs (floor + marker, same as the web painter) ----
        if (theme != null) {
            paintDisc(g, DesktopPaint.endpointMarker(layout, current.metadata().start()),
                    theme.start());
            paintDisc(g, DesktopPaint.endpointMarker(layout, current.metadata().goal()),
                    theme.goal());
        }

        // ---- 4) player marker, then the web victory ring ----
        DesktopPaint.Marker mark = DesktopPaint.playerMarker(layout, playerPos);
        if (mark != null && theme != null) {
            paintDisc(g, mark, theme.player());
        }
        if (reachedGoal) {
            paintRing(g, DesktopPaint.victoryRing(layout, current.metadata().goal()));
        }
        syncLegend();
    }

    private void syncLegend() {
        if (legendBox == null) {
            return;
        }
        DesktopPaint.Fog fog = fogScene();
        List<String> keys = DesktopPaint.legendKeys(
                current != null,
                currentPath != null && !currentPath.isEmpty(),
                playerWalk.size() > 1,
                current != null && current.hotspots() != null && !current.hotspots().isEmpty(),
                fog,
                currentCuts != null && currentCuts.chokepoints() != null
                        && !currentCuts.chokepoints().isEmpty());
        legendBox.setVisible(!keys.isEmpty());
        if (exportBox != null) {
            exportBox.setVisible(current != null);
        }
        showLegendKey(legendStart, keys.contains("start"));
        showLegendKey(legendGoal, keys.contains("goal"));
        showLegendKey(legendPath, keys.contains("path"));
        showLegendKey(legendPlayer, keys.contains("player"));
        showLegendKey(legendHotspot, keys.contains("hotspot"));
        showLegendKey(legendFog, keys.contains("fog"));
        showLegendKey(legendChoke, keys.contains("choke"));
    }

    private boolean fogOn() {
        return fogToggle != null && fogToggle.isSelected() && current != null;
    }

    private DesktopPaint.Fog fogScene() {
        if (!fogOn()) {
            return null;
        }
        Point target = current.metadata().goal();
        Point goal = reachedGoal || (playerPos != null && playerPos.equals(target))
                ? target : null;
        return DesktopPaint.Fog.of(playerWalk, playerPos, goal);
    }

    private void paintFogDungeon(GraphicsContext g, DesktopPaint.Layout layout,
                                 TileType[][] tiles, Theme theme, DesktopPaint.Fog fog) {
        for (int r = 0; r < layout.tileRows(); r++) {
            for (int c = 0; c < layout.tileCols(); c++) {
                if (!DesktopPaint.fogRevealsTile(fog, r, c)) {
                    continue;
                }
                TileType role = DesktopPaint.floorRole(tiles[r][c]);
                if (role == TileType.WALL) {
                    g.setFill(theme != null ? theme.wall() : Color.web("#0b0f14"));
                    g.fillRect(layout.x(c), layout.y(r), layout.w(c), layout.h(r));
                    continue;
                }
                g.setFill(Color.web(DesktopPaint.fogFloor(fog, r, c)));
                g.fillRect(layout.x(c), layout.y(r), layout.w(c), layout.h(r));
                paintHairline(g, DesktopPaint.floorHiStroke(layout, r, c,
                        DesktopPaint.fogLamp(fog, r, c)));
            }
        }
        if (!playerWalk.isEmpty() && theme != null) {
            g.setGlobalAlpha(0.32);
            g.setFill(theme.player());
            for (DesktopPaint.TileRect tile : DesktopPaint.walkOverlay(playerWalk)) {
                g.fillRect(layout.x(tile.tileCol()), layout.y(tile.tileRow()),
                        layout.w(tile.tileCol()), layout.h(tile.tileRow()));
            }
            g.setGlobalAlpha(1);
        }
        Point start = current.metadata().start();
        if (theme != null && start != null && fog.seen(start.row(), start.col())) {
            paintDisc(g, DesktopPaint.endpointMarker(layout, start), theme.start());
        }
        if (theme != null && fog.goal() != null) {
            paintDisc(g, DesktopPaint.endpointMarker(layout, fog.goal()), theme.goal());
        }
        DesktopPaint.Marker mark = DesktopPaint.playerMarker(layout, fog.position());
        if (mark != null && theme != null) {
            paintDisc(g, mark, theme.player());
        }
        if (reachedGoal) {
            paintRing(g, DesktopPaint.victoryRing(layout, current.metadata().goal()));
        }
    }

    private static void showLegendKey(Label key, boolean on) {
        if (key == null) {
            return;
        }
        key.setVisible(on);
        key.setManaged(on);
    }

    private void resetWalk(Point start) {
        playerWalk.clear();
        if (start != null) {
            playerWalk.add(start);
        }
    }

    private void rememberWalk(Point cell) {
        if (cell == null) {
            return;
        }
        if (playerWalk.isEmpty() || !playerWalk.get(playerWalk.size() - 1).equals(cell)) {
            playerWalk.add(cell);
        }
    }

    private static void paintDisc(GraphicsContext g, DesktopPaint.Marker mark, Color color) {
        if (mark == null || color == null) {
            return;
        }
        Color glow = color.deriveColor(0, 1, 1, 0.22);
        double pad = mark.size() * 0.32;
        g.setFill(glow);
        g.fillOval(mark.x() - pad / 2, mark.y() - pad / 2,
                mark.size() + pad, mark.size() + pad);
        g.setFill(color);
        g.fillOval(mark.x(), mark.y(), mark.size(), mark.size());
    }

    private static void paintHairline(GraphicsContext g, DesktopPaint.Hairline line) {
        if (line == null) {
            return;
        }
        g.setFill(Color.web(DesktopPaint.FLOOR_HI));
        g.fillRect(line.x(), line.y(), line.w(), line.h());
    }

    private static void paintRing(GraphicsContext g, DesktopPaint.Ring ring) {
        if (ring == null) {
            return;
        }
        g.setStroke(Color.web(DesktopPaint.VICTORY_GOLD));
        g.setLineWidth(ring.width());
        g.strokeOval(ring.cx() - ring.radius(), ring.cy() - ring.radius(),
                ring.radius() * 2, ring.radius() * 2);
    }

    /** Resolve a tile glyph to a theme color. Defensive — unknown enum cases fall back to passage. */
    private static Color colorFor(TileType tile, Theme theme) {
        if (theme == null) {
            return tile == TileType.WALL ? Color.web("#222222") : Color.web("#cccccc");
        }
        return switch (tile) {
            case WALL     -> theme.wall();
            case PASSAGE  -> theme.passage();
            case START    -> theme.start();
            case GOAL     -> theme.goal();
            case PATH     -> theme.path();
            case VISITED  -> theme.visited();
            case FRONTIER -> theme.frontier();
            case PLAYER   -> theme.player();
        };
    }
}
