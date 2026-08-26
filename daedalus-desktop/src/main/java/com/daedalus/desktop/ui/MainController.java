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
import javafx.scene.layout.Pane;
import javafx.scene.paint.Color;
import org.springframework.stereotype.Component;

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
    @FXML private TextField seedField;
    @FXML private Button generateButton;     // referenced from FXML, kept for future enable/disable
    @FXML private ComboBox<String> solverChoice;
    @FXML private Button solveButton;        // ditto
    @FXML private Button resetButton;        // ditto
    @FXML private Pane canvasParent;
    @FXML private Canvas canvas;
    @FXML private Label statusLabel;

    /** Last successfully-generated maze; held so resize events can re-render it. */
    private MazeGenerationService.Cached current;

    /** Solver path overlay (cell-coordinate {@link Point}s) — null when no solve has run since the last Generate. */
    private List<Point> currentPath;

    /** Player marker position. Set on Generate / Reset; updated on arrow-key moves. */
    private Point playerPos;

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

        // Canvas tracks its parent's size, redraws on every change so the existing maze
        // rescales when the window is resized.
        canvas.widthProperty().bind(canvasParent.widthProperty());
        canvas.heightProperty().bind(canvasParent.heightProperty());
        canvas.widthProperty().addListener((obs, oldV, newV) -> redraw());
        canvas.heightProperty().addListener((obs, oldV, newV) -> redraw());

        // Keyboard handler for player movement. Canvas grabs focus on Generate so arrow
        // keys "just work" without an explicit click. Pressing a movement key while a text
        // field is focused (e.g. typing in Seed) goes to the text field; that's the right
        // behavior — explicit click on the maze area transfers focus back.
        canvas.setFocusTraversable(true);
        canvas.setOnMouseClicked(e -> canvas.requestFocus());
        canvas.setOnKeyPressed(this::onKeyPressed);
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

        long t0 = System.nanoTime();
        Task<MazeGenerationService.Cached> task = new Task<>() {
            @Override
            protected MazeGenerationService.Cached call() throws Exception {
                return work.generateJob(genId, rows, cols, seed).call();
            }
        };
        task.setOnSucceeded(e -> {
            current = task.getValue();
            long elapsedMs = (System.nanoTime() - t0) / 1_000_000L;

            // Fresh maze invalidates any prior solve overlay and snaps the player to start.
            currentPath = null;
            playerPos = current.metadata().start();
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
            currentPath = task.getValue().path();
            redraw();
            canvas.requestFocus();
            statusLabel.setText(String.format(
                    "Solved with %s in %dms — %d cells on the path.",
                    solverId, elapsedMs, currentPath == null ? 0 : currentPath.size()));
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
        if (step.reachedGoal()) {
            reachedGoal = true;
            statusLabel.setText("Reached the goal!  Press Reset, or Generate a new maze.");
        }
        redraw();
    }

    // ---------- rendering ----------

    /**
     * Paint {@link #current} onto the canvas. Layered:
     * <ol>
     *   <li>Background fill.</li>
     *   <li>Tile grid via {@link MazeGrid#toTileGrid()} — passages, walls, start, goal.</li>
     *   <li>Solve path overlay (if {@link #currentPath} is set) — drawn under start/goal so
     *       endpoint markers stay visible.</li>
     *   <li>Player marker — drawn last so it's always on top of whatever is underneath.</li>
     * </ol>
     * Square cells, centered with letterboxing on the longer axis so the maze isn't stretched.
     */
    private void redraw() {
        double w = canvas.getWidth();
        double h = canvas.getHeight();
        if (w <= 0 || h <= 0) return;

        Theme theme = themeManager.active();
        GraphicsContext g = canvas.getGraphicsContext2D();

        Color bg = theme != null ? theme.background() : Color.web("#000000");
        g.setFill(bg);
        g.fillRect(0, 0, w, h);

        if (current == null) return;

        TileType[][] tiles = current.grid().toTileGrid();
        DesktopPaint.Layout layout = DesktopPaint.Layout.fit(
                tiles.length, tiles[0].length, w, h);
        if (layout == null) return;

        // ---- 1) tile grid ----
        for (int r = 0; r < layout.tileRows(); r++) {
            for (int c = 0; c < layout.tileCols(); c++) {
                g.setFill(colorFor(DesktopPaint.roleFor(tiles[r][c]), theme));
                g.fillRect(layout.x(c), layout.y(r), layout.cellSize(), layout.cellSize());
            }
        }

        // ---- 2) solve-path overlay ----
        if (currentPath != null && !currentPath.isEmpty() && theme != null) {
            g.setFill(theme.path());
            for (DesktopPaint.TileRect tile : DesktopPaint.pathOverlay(
                    currentPath, current.metadata().start(), current.metadata().goal())) {
                g.fillRect(layout.x(tile.tileCol()), layout.y(tile.tileRow()),
                        layout.cellSize(), layout.cellSize());
            }
        }

        // ---- 3) player marker ----
        DesktopPaint.Marker mark = DesktopPaint.playerMarker(layout, playerPos);
        if (mark != null && theme != null) {
            g.setFill(reachedGoal ? theme.path() : theme.player());
            g.fillOval(mark.x(), mark.y(), mark.size(), mark.size());
        }
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
