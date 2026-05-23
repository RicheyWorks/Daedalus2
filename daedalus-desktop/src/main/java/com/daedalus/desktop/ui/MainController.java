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
 * {@link GeneratorRegistry}, {@link SolverRegistry}, {@link MazeGenerationService},
 * {@link MazeSolverService}, {@link ThemeManager}.
 *
 * <p>Responsibilities:
 * <ul>
 *   <li>Populate generator / solver dropdowns from the live registries (built-ins + plugins).</li>
 *   <li>Run a generation on Generate — delegates to {@code MazeGenerationService} so plugin
 *       events and metrics fire exactly the same way as the REST surface.</li>
 *   <li>Run a solve on Solve — same delegation rationale; overlays the returned path on
 *       the canvas in the theme's {@code path()} color.</li>
 *   <li>Track a movable player marker; arrow keys / WASD walk it through open walls,
 *       reaching the goal flips the status bar to a celebration message.</li>
 *   <li>Render everything on a {@link Canvas}, repaint on resize.</li>
 * </ul>
 *
 * <p>JavaFX threading: every {@code @FXML} method runs on the JavaFX Application Thread,
 * which is also the thread that mutates the Canvas. Generation and solve are fast enough
 * at the Spinner-bounded sizes (≤ 128² = 16 384 cells) that we don't background them; if
 * a later change pushes that into the multi-second range, wrap the calls in a
 * {@link javafx.concurrent.Task} and bind the status label to its {@code messageProperty}.
 */
@Component
public class MainController {

    /** Maximum row / col spinner value; matches REST validation cap and keeps the canvas legible. */
    private static final int MAX_DIM = 128;

    private final GeneratorRegistry generatorRegistry;
    private final SolverRegistry solverRegistry;
    private final MazeGenerationService generationService;
    private final MazeSolverService solverService;
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
                          MazeGenerationService generationService,
                          MazeSolverService solverService,
                          ThemeManager themeManager) {
        this.generatorRegistry = generatorRegistry;
        this.solverRegistry = solverRegistry;
        this.generationService = generationService;
        this.solverService = solverService;
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

        try {
            long t0 = System.nanoTime();
            current = generationService.generate(genId, rows, cols, seed);
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
        } catch (RuntimeException e) {
            statusLabel.setText("Generation failed: " + e.getMessage());
        }
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
        try {
            long t0 = System.nanoTime();
            MazeSolverService.Result result = solverService.solve(
                    solverId, current.grid(), current.metadata().id());
            long elapsedMs = (System.nanoTime() - t0) / 1_000_000L;

            currentPath = result.path();
            redraw();
            canvas.requestFocus();

            statusLabel.setText(String.format(
                    "Solved with %s in %dms — %d cells on the path.",
                    solverId, elapsedMs, currentPath == null ? 0 : currentPath.size()));
        } catch (RuntimeException e) {
            statusLabel.setText("Solve failed: " + e.getMessage());
        }
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
        if (current == null || playerPos == null) return;
        if (reachedGoal) return;

        if (!current.grid().cell(playerPos).isOpen(dir)) {
            // Hitting a wall — silent, no status spam (status is the most distracting place
            // to flash this; let the player keep tapping keys).
            return;
        }
        Point next = playerPos.step(dir);
        if (!current.grid().inBounds(next)) return;   // defensive — shouldn't happen if isOpen is correct
        playerPos = next;

        if (playerPos.equals(current.metadata().goal())) {
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
        int tr = tiles.length;
        int tc = tiles[0].length;

        double cellSize = Math.max(1.0, Math.floor(Math.min(w / tc, h / tr)));
        double drawW = cellSize * tc;
        double drawH = cellSize * tr;
        double offsetX = Math.floor((w - drawW) / 2);
        double offsetY = Math.floor((h - drawH) / 2);

        // ---- 1) tile grid ----
        for (int r = 0; r < tr; r++) {
            for (int c = 0; c < tc; c++) {
                Color color = colorFor(tiles[r][c], theme);
                g.setFill(color);
                g.fillRect(offsetX + c * cellSize, offsetY + r * cellSize, cellSize, cellSize);
            }
        }

        // ---- 2) solve-path overlay ----
        if (currentPath != null && !currentPath.isEmpty() && theme != null) {
            g.setFill(theme.path());
            Point start = current.metadata().start();
            Point goal = current.metadata().goal();

            for (int i = 0; i < currentPath.size(); i++) {
                Point p = currentPath.get(i);
                if (p.equals(start) || p.equals(goal)) continue;   // preserve endpoint colors
                fillTile(g, offsetX, offsetY, cellSize, 2 * p.row() + 1, 2 * p.col() + 1);

                // Connecting opening to the previous cell — paints the wall-tile carved
                // between them so the path renders continuously, not as dots.
                if (i > 0) {
                    Point prev = currentPath.get(i - 1);
                    int connR = prev.row() + p.row() + 1;
                    int connC = prev.col() + p.col() + 1;
                    fillTile(g, offsetX, offsetY, cellSize, connR, connC);
                }
            }
        }

        // ---- 3) player marker ----
        if (playerPos != null && theme != null) {
            // Slightly inset square so the player reads as distinct from a solid passage tile;
            // color flips to gold (path color) when reachedGoal so victory is unambiguous.
            Color playerColor = reachedGoal ? theme.path() : theme.player();
            g.setFill(playerColor);
            double inset = Math.max(1.0, cellSize * 0.1);
            double px = offsetX + (2 * playerPos.col() + 1) * cellSize + inset;
            double py = offsetY + (2 * playerPos.row() + 1) * cellSize + inset;
            double pSize = cellSize - 2 * inset;
            g.fillOval(px, py, pSize, pSize);
        }
    }

    /** Helper: paint a single tile cell at the given tile-grid (row, col). */
    private static void fillTile(GraphicsContext g, double offsetX, double offsetY,
                                 double cellSize, int tileRow, int tileCol) {
        g.fillRect(offsetX + tileCol * cellSize, offsetY + tileRow * cellSize, cellSize, cellSize);
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
