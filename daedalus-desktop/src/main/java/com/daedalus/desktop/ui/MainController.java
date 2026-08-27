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
import javafx.scene.control.ComboBox;
import javafx.scene.control.Label;
import javafx.scene.control.Spinner;
import javafx.scene.control.SpinnerValueFactory;
import javafx.scene.control.TextField;
import javafx.scene.input.KeyCode;
import javafx.scene.input.KeyEvent;
import javafx.scene.layout.HBox;
import javafx.scene.layout.Pane;
import javafx.scene.paint.Color;
import javafx.scene.text.Font;
import javafx.scene.text.FontWeight;
import javafx.scene.text.TextAlignment;
import javafx.scene.transform.Scale;
import javafx.stage.Window;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

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
 *   <li>Track a movable player marker; arrow keys / WASD walk it through open walls,
 *       reaching the goal flips the status bar to a celebration message.</li>
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
    @FXML private TextField seedField;
    @FXML private Button generateButton;     // referenced from FXML, kept for future enable/disable
    @FXML private ComboBox<String> solverChoice;
    @FXML private Button solveButton;        // ditto
    @FXML private Button resetButton;        // ditto
    @FXML private Pane canvasParent;
    @FXML private Canvas canvas;
    @FXML private HBox legendBox;
    @FXML private Label legendPath;
    @FXML private Label legendPlayer;
    @FXML private Label legendHotspot;
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

        rowsSpinner.setValueFactory(new SpinnerValueFactory.IntegerSpinnerValueFactory(2, MAX_DIM, 30));
        colsSpinner.setValueFactory(new SpinnerValueFactory.IntegerSpinnerValueFactory(2, MAX_DIM, 40));
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
        canvas.setOnMouseClicked(e -> canvas.requestFocus());
        canvas.setOnKeyPressed(this::onKeyPressed);

        if (legendBox != null) {
            legendBox.layoutXProperty().bind(
                    canvasParent.widthProperty().subtract(legendBox.widthProperty()).divide(2));
            legendBox.layoutYProperty().bind(
                    canvasParent.heightProperty().subtract(legendBox.heightProperty()).subtract(4));
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

        long t0 = System.nanoTime();
        Task<MazeGenerationService.Cached> task = new Task<>() {
            @Override
            protected MazeGenerationService.Cached call() throws Exception {
                return work.generateJob(genId, rows, cols, seed, spots).call();
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

            redraw();
            canvas.requestFocus();

            String actualId = current.metadata().generatorId();
            String genNote = actualId.equals(genId) ? "" : "  (fell back from " + genId + ")";
            statusLabel.setText(String.format(
                    "Drew %d×%d via %s, seed=%d, %dms%s — arrow keys / WASD to walk.",
                    rows, cols, actualId, seed, elapsedMs, genNote));
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

        Color bg = theme != null ? theme.background() : Color.web("#000000");
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

        // ---- 1) tile grid ----
        for (int r = 0; r < layout.tileRows(); r++) {
            for (int c = 0; c < layout.tileCols(); c++) {
                g.setFill(colorFor(DesktopPaint.floorRole(tiles[r][c]), theme));
                g.fillRect(layout.x(c), layout.y(r), layout.w(c), layout.h(r));
            }
        }

        if (current.hotspots() != null && !current.hotspots().isEmpty()) {
            g.setFill(Color.web("#e5484d"));
            g.setGlobalAlpha(0.4);
            for (DesktopPaint.TileRect tile : DesktopPaint.hotspotOverlay(current.hotspots(), tiles)) {
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
            g.setFill(theme.path());
            for (DesktopPaint.TileRect tile : DesktopPaint.pathOverlay(
                    currentPath, current.metadata().start(), current.metadata().goal())) {
                g.fillRect(layout.x(tile.tileCol()), layout.y(tile.tileRow()),
                        layout.w(tile.tileCol()), layout.h(tile.tileRow()));
            }
        }

        // ---- 3) start / goal discs (floor + marker, same as the web painter) ----
        if (theme != null) {
            paintDisc(g, DesktopPaint.endpointMarker(layout, current.metadata().start()),
                    theme.start());
            paintDisc(g, DesktopPaint.endpointMarker(layout, current.metadata().goal()),
                    theme.goal());
        }

        // ---- 4) player marker ----
        DesktopPaint.Marker mark = DesktopPaint.playerMarker(layout, playerPos);
        if (mark != null && theme != null) {
            paintDisc(g, mark, reachedGoal ? theme.path() : theme.player());
        }
        syncLegend();
    }

    private void syncLegend() {
        if (legendBox == null) {
            return;
        }
        List<String> keys = DesktopPaint.legendKeys(
                current != null,
                currentPath != null && !currentPath.isEmpty(),
                playerWalk.size() > 1,
                current != null && current.hotspots() != null && !current.hotspots().isEmpty());
        legendBox.setVisible(!keys.isEmpty());
        showLegendKey(legendPath, keys.contains("path"));
        showLegendKey(legendPlayer, keys.contains("player"));
        showLegendKey(legendHotspot, keys.contains("hotspot"));
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
