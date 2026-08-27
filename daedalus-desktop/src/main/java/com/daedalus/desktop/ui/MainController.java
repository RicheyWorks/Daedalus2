// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.desktop.ui.themes.Theme;
import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.model.Direction;
import com.daedalus.model.GameSession;
import com.daedalus.model.Point;
import com.daedalus.model.TileType;
import com.daedalus.server.service.HeuristicLensService;
import com.daedalus.server.service.LivingMazeService;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.MazeSolverService;
import com.daedalus.server.service.TrafficService;
import com.daedalus.theory.LongestPath;
import javafx.animation.AnimationTimer;
import javafx.animation.KeyFrame;
import javafx.animation.Timeline;
import javafx.application.Platform;
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
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

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
    @FXML private CheckBox hardestToggle;
    @FXML private CheckBox sanctuaryToggle;
    @FXML private ComboBox<LensPick> lensChoice;
    @FXML private CheckBox raceToggle;
    @FXML private CheckBox huntToggle;
    @FXML private CheckBox liveToggle;
    @FXML private CheckBox hardToggle;
    @FXML private CheckBox jamToggle;
    @FXML private CheckBox allToggle;
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
    @FXML private Label legendHardest;
    @FXML private Label legendSanctuary;
    @FXML private Label legendLens;
    @FXML private Label legendRace;
    @FXML private Label legendWaypoint;
    @FXML private Label legendGhost;
    @FXML private Label legendCompare;
    @FXML private Label statusLabel;

    /** Last successfully-generated maze; held so resize events can re-render it. */
    private MazeGenerationService.Cached current;

    /** Solver path overlay (cell-coordinate {@link Point}s) — null when no solve has run since the last Generate. */
    private List<Point> currentPath;

    /** Full solve route; {@link #currentPath} is the visible prefix while it unfolds. */
    private List<Point> solvedPath;

    /** Solver to re-run quietly on living / traffic ticks — same as the web refresh. */
    private String followSolver;
    private int followGen;

    /** Recorded search order; {@link #currentExpansions} is the visible prefix. */
    private List<Point> solvedExpansions;
    private List<Point> currentExpansions;

    private AnimationTimer pathReveal;

    /** Polls the living snapshot at the server tick interval. */
    private Timeline liveWatch;

    /** Polls congested weights at the traffic tick interval. */
    private Timeline trafficWatch;

    /** Replays the maze's best finish — same 100ms tick as {@code ghost.js}. */
    private Timeline ghostWatch;
    private DesktopWork.GhostTape ghostTape;
    private long ghostStartedNs;
    private boolean ghostDone;

    private final List<GameSession.TimedMove> walkMoves = new ArrayList<>();
    private long walkStartedNs;

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

    /** Hardest simple route — cleared on Generate and Fog. */
    private LongestPath.LongPath currentHardest;

    /** k-center safe points — cleared on Generate and Fog. */
    private DesktopPaint.Sanctuaries currentSanctuaries;

    /** Heuristic lens — cleared on Generate and Fog. */
    private DesktopPaint.LensWash currentLens;

    /** Every solver's route — cleared on Generate, Fog, Race, and Solve. */
    private DesktopPaint.Compare currentCompare;

    /** Two-solver arena — cleared on Generate, Fog, and a plain Solve. */
    private DesktopPaint.Race currentRace;
    private double raceFrontA;
    private double racePathA;
    private double raceFrontB;
    private double racePathB;

    /** Waypoint hunt — cleared on Generate, Fog, Solve, and Race. */
    private DesktopPaint.Hunt currentHunt;
    private final Set<Point> huntGot = new LinkedHashSet<>();

    /** Compact picker labels — same four heuristics as the web {@code lensH} select. */
    private enum LensPick {
        OFF("Off", null),
        MANHATTAN("Manh", HeuristicLensService.Heuristic.MANHATTAN),
        LANDMARK("Land", HeuristicLensService.Heuristic.LANDMARK),
        TIE("Tie", HeuristicLensService.Heuristic.MANHATTAN_TIE_BROKEN),
        INFLATED("×3", HeuristicLensService.Heuristic.INFLATED);

        private final String label;
        private final HeuristicLensService.Heuristic heuristic;

        LensPick(String label, HeuristicLensService.Heuristic heuristic) {
            this.label = label;
            this.heuristic = heuristic;
        }

        @Override
        public String toString() {
            return label;
        }
    }

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
        if (lensChoice != null) {
            lensChoice.getItems().setAll(LensPick.values());
            lensChoice.getSelectionModel().select(LensPick.OFF);
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

        stopLiveWatch();
        if (liveToggle != null) {
            liveToggle.setSelected(false);
        }
        if (hardToggle != null) {
            hardToggle.setDisable(false);
        }
        stopTrafficWatch();
        if (jamToggle != null) {
            jamToggle.setSelected(false);
        }

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
            currentExpansions = null;
            solvedExpansions = null;
            clearRace();
            clearHunt();
            clearCompare();
            clearFollow();
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
        clearRace();
        clearHunt();
        clearGhost();
        clearCompare();
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
            solvedExpansions = task.getValue().expansions();
            currentPath = List.of();
            currentExpansions = List.of();
            followSolver = solverId;
            startSolveReveal();
            canvas.requestFocus();
            int expanded = solvedExpansions == null ? 0 : solvedExpansions.size();
            statusLabel.setText(String.format(
                    "Solved with %s in %dms — %d cells on the path, %d expanded.",
                    solverId, elapsedMs, solvedPath == null ? 0 : solvedPath.size(),
                    expanded));
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
        huntGot.clear();
        clearGhost();
        if (currentHunt == null) {
            summonGhost();
        }
        redraw();
        canvas.requestFocus();
        if (ghostTape != null) {
            return;
        }
        statusLabel.setText(currentHunt == null
                ? "Reset to start."
                : "Hunt reset — collect " + currentHunt.waypoints().size()
                        + " coins then the goal.");
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
        clearGhost();
        clearLens();
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
        currentHardest = null;
        if (cutsToggle != null) {
            cutsToggle.setSelected(false);
        }
        if (hardestToggle != null) {
            hardestToggle.setSelected(false);
        }
        currentSanctuaries = null;
        if (sanctuaryToggle != null) {
            sanctuaryToggle.setSelected(false);
        }
        clearLens();
        clearGhost();
    }

    private void clearCompare() {
        currentCompare = null;
        if (allToggle != null) {
            allToggle.setSelected(false);
        }
    }

    private void clearFollow() {
        followSolver = null;
        followGen++;
    }

    /**
     * Keep the ribbon and drop the search wash — living / traffic
     * ticks re-solve quietly like {@code living.js} {@code refresh}.
     */
    private void keepFollowRoute() {
        stopPathReveal();
        currentExpansions = null;
        solvedExpansions = null;
        if ((solvedPath != null && !solvedPath.isEmpty())
                || (currentPath != null && !currentPath.isEmpty())) {
            followSolver = solverChoice.getValue();
            if (solvedPath != null) {
                currentPath = solvedPath;
            }
        } else {
            clearFollow();
        }
    }

    private void refreshFollowRoute(UUID mazeId) {
        if (followSolver == null || fogOn() || current == null || mazeId == null) {
            return;
        }
        final int gen = ++followGen;
        final String solver = followSolver;
        final var grid = current.grid();
        Thread worker = new Thread(() -> {
            try {
                var result = work.solveJob(solver, grid, mazeId, false).call();
                Platform.runLater(() -> {
                    if (gen != followGen || current == null
                            || !mazeId.equals(current.metadata().id())) {
                        return;
                    }
                    solvedPath = result.path();
                    currentPath = result.path();
                    currentExpansions = null;
                    solvedExpansions = null;
                    redraw();
                });
            } catch (Exception ignored) {
                // budget refusal: keep the last ribbon
            }
        }, "daedalus-desktop-follow");
        worker.setDaemon(true);
        worker.start();
    }

    private void clearGhost() {
        stopGhostWatch();
        ghostTape = null;
        ghostDone = false;
    }

    private void stopGhostWatch() {
        if (ghostWatch != null) {
            ghostWatch.stop();
            ghostWatch = null;
        }
    }

    private void summonGhost() {
        if (current == null || fogOn()) {
            return;
        }
        DesktopWork.GhostTape tape = work.ghostOf(current.metadata().id());
        if (tape == null || tape.moves().isEmpty()) {
            return;
        }
        ghostTape = tape;
        ghostStartedNs = System.nanoTime();
        ghostDone = false;
        stopGhostWatch();
        ghostWatch = new Timeline(new KeyFrame(javafx.util.Duration.millis(100),
                e -> pulseGhost()));
        ghostWatch.setCycleCount(Timeline.INDEFINITE);
        ghostWatch.play();
        statusLabel.setText(String.format(
                "Ghost summoned: %s's best run (%.1fs) — beat it.",
                tape.playerName(), tape.elapsedMs() / 1000.0));
    }

    private void pulseGhost() {
        if (ghostTape == null) {
            stopGhostWatch();
            return;
        }
        if (ghostDone) {
            stopGhostWatch();
            redraw();
            return;
        }
        long elapsed = (System.nanoTime() - ghostStartedNs) / 1_000_000L;
        boolean stillGoing = false;
        for (GameSession.TimedMove step : ghostTape.moves()) {
            if (step.tMs() > elapsed) {
                stillGoing = true;
                break;
            }
        }
        if (!stillGoing) {
            ghostDone = true;
            stopGhostWatch();
            if (!reachedGoal) {
                statusLabel.setText(String.format("The ghost finished its run (%.1fs).",
                        ghostTape.elapsedMs() / 1000.0));
            }
        }
        redraw();
    }

    private List<Point> ghostWalkNow() {
        if (ghostTape == null) {
            return List.of();
        }
        long elapsed = (System.nanoTime() - ghostStartedNs) / 1_000_000L;
        return DesktopPaint.ghostPrefix(ghostTape.start(), ghostTape.moves(), elapsed);
    }

    private void clearRace() {
        currentRace = null;
        raceFrontA = 0;
        racePathA = 0;
        raceFrontB = 0;
        racePathB = 0;
        if (raceToggle != null) {
            raceToggle.setSelected(false);
        }
    }

    private void clearHunt() {
        currentHunt = null;
        huntGot.clear();
        if (huntToggle != null) {
            huntToggle.setSelected(false);
        }
    }

    /**
     * Wired from the well's Live checkbox. Same Bring to life as the web —
     * the maze erodes in the cache and the well follows each tick.
     */
    @FXML
    public void onLive() {
        if (liveToggle == null) {
            return;
        }
        if (!liveToggle.isSelected()) {
            if (current != null && work.liveStatus(current.metadata().id()).active()) {
                liveToggle.setSelected(true);
            } else {
                stopLiveWatch();
            }
            return;
        }
        if (current == null) {
            liveToggle.setSelected(false);
            statusLabel.setText("Generate a maze first, then check Live.");
            return;
        }
        keepFollowRoute();
        clearRace();
        clearTheory();
        clearCompare();
        UUID mazeId = current.metadata().id();
        boolean harden = hardToggle != null && hardToggle.isSelected();
        try {
            LivingMazeService.LiveStatus status = work.startLive(mazeId,
                    current.metadata().seed(), harden);
            if (hardToggle != null) {
                hardToggle.setDisable(true);
            }
            watchLive(mazeId, status.tickMillis());
            statusLabel.setText(String.format(
                    "Maze is alive — %d ticks, one every %.1fs%s.",
                    status.ticksRequested(), status.tickMillis() / 1000.0,
                    harden ? " (eroding and hardening)" : " (erosion only)"));
        } catch (LivingMazeService.CapacityExceededException full) {
            liveToggle.setSelected(false);
            statusLabel.setText(full.getMessage());
        }
        canvas.requestFocus();
    }

    private void watchLive(UUID mazeId, long tickMillis) {
        stopLiveWatch();
        long interval = Math.max(50L, tickMillis);
        liveWatch = new Timeline(new KeyFrame(javafx.util.Duration.millis(interval),
                e -> pulseLive(mazeId)));
        liveWatch.setCycleCount(Timeline.INDEFINITE);
        liveWatch.play();
    }

    private void pulseLive(UUID mazeId) {
        if (current == null || !mazeId.equals(current.metadata().id())) {
            stopLiveWatch();
            return;
        }
        MazeGenerationService.Cached snap = work.snapshot(mazeId);
        LivingMazeService.LiveStatus status = work.liveStatus(mazeId);
        if (snap != null) {
            current = snap;
            if (currentHunt != null) {
                currentHunt = DesktopPaint.Hunt.retarget(current.grid(),
                        currentHunt.waypoints());
            }
            refreshFollowRoute(mazeId);
            redraw();
        }
        if (!status.active()) {
            stopLiveWatch();
            if (liveToggle != null) {
                liveToggle.setSelected(false);
            }
            if (hardToggle != null) {
                hardToggle.setDisable(false);
            }
            statusLabel.setText(status.settled()
                    ? "Maze settled after " + status.ticksDone() + " ticks."
                    : "Living run ended.");
            return;
        }
        statusLabel.setText(String.format("Alive — tick %d / %d.",
                status.ticksDone(), status.ticksRequested()));
    }

    private void stopLiveWatch() {
        if (liveWatch != null) {
            liveWatch.stop();
            liveWatch = null;
        }
    }

    /**
     * Wired from the well's Jam checkbox. Same Simulate traffic as the web —
     * walked cells bloom cost, then cool off.
     */
    @FXML
    public void onJam() {
        if (jamToggle == null) {
            return;
        }
        if (!jamToggle.isSelected()) {
            if (current != null && work.trafficStatus(current.metadata().id()).active()) {
                jamToggle.setSelected(true);
            } else {
                stopTrafficWatch();
            }
            return;
        }
        if (current == null) {
            jamToggle.setSelected(false);
            statusLabel.setText("Generate a maze first, then check Jam.");
            return;
        }
        keepFollowRoute();
        clearRace();
        clearLens();
        clearCompare();
        UUID mazeId = current.metadata().id();
        try {
            TrafficService.TrafficStatus status = work.enableTraffic(mazeId);
            MazeGenerationService.Cached snap = work.snapshot(mazeId);
            if (snap != null) {
                current = snap;
            }
            refreshFollowRoute(mazeId);
            watchTraffic(mazeId, status.tickMillis());
            statusLabel.setText(String.format(
                    "Traffic tracking on — walk and watch costs bloom, one pulse every %.1fs.",
                    status.tickMillis() / 1000.0));
        } catch (TrafficService.CapacityExceededException full) {
            jamToggle.setSelected(false);
            statusLabel.setText(full.getMessage());
        }
        redraw();
        canvas.requestFocus();
    }

    private void watchTraffic(UUID mazeId, long tickMillis) {
        stopTrafficWatch();
        long interval = Math.max(50L, tickMillis);
        trafficWatch = new Timeline(new KeyFrame(javafx.util.Duration.millis(interval),
                e -> pulseTraffic(mazeId)));
        trafficWatch.setCycleCount(Timeline.INDEFINITE);
        trafficWatch.play();
    }

    private void pulseTraffic(UUID mazeId) {
        if (current == null || !mazeId.equals(current.metadata().id())) {
            stopTrafficWatch();
            return;
        }
        MazeGenerationService.Cached snap = work.snapshot(mazeId);
        TrafficService.TrafficStatus status = work.trafficStatus(mazeId);
        if (snap != null) {
            current = snap;
            refreshFollowRoute(mazeId);
            redraw();
        }
        if (!status.active()) {
            stopTrafficWatch();
            if (jamToggle != null) {
                jamToggle.setSelected(false);
            }
            int n = current.hotspots() == null ? 0 : current.hotspots().size();
            statusLabel.setText(n == 0
                    ? "Traffic fully decayed — tracking retired."
                    : "Traffic tracking ended.");
            return;
        }
        int congested = current.hotspots() == null ? 0 : current.hotspots().size();
        statusLabel.setText(congested == 0
                ? "Traffic — walk to bloom costs."
                : "Traffic — " + congested
                        + (congested == 1 ? " congested cell." : " congested cells."));
    }

    private void stopTrafficWatch() {
        if (trafficWatch != null) {
            trafficWatch.stop();
            trafficWatch = null;
        }
    }

    /**
     * Wired from the well's All checkbox. Same Compare all as the web —
     * every solver's route stacked so agreement is a brighter corridor.
     */
    @FXML
    public void onAll() {
        if (allToggle == null || !allToggle.isSelected()) {
            currentCompare = null;
            redraw();
            return;
        }
        if (current == null) {
            allToggle.setSelected(false);
            statusLabel.setText("Generate a maze first, then check All.");
            return;
        }
        if (fogOn()) {
            allToggle.setSelected(false);
            statusLabel.setText("Fog hides the compared routes — uncheck Fog to compare.");
            return;
        }
        List<String> ids = solverChoice.getItems();
        if (ids == null || ids.isEmpty()) {
            allToggle.setSelected(false);
            statusLabel.setText("No solvers are registered.");
            return;
        }
        stopPathReveal();
        currentPath = null;
        solvedPath = null;
        currentExpansions = null;
        solvedExpansions = null;
        clearRace();
        clearHunt();
        clearTheory();
        clearFollow();
        allToggle.setSelected(true);
        var grid = current.grid();
        var mazeId = current.metadata().id();
        Task<DesktopPaint.Compare> task = new Task<>() {
            @Override
            protected DesktopPaint.Compare call() throws Exception {
                return work.compareJob(ids, grid, mazeId).call();
            }
        };
        task.setOnSucceeded(e -> {
            currentCompare = task.getValue();
            int ok = 0;
            int n = 0;
            if (currentCompare != null && currentCompare.lanes() != null) {
                n = currentCompare.lanes().size();
                for (DesktopPaint.CompareLane lane : currentCompare.lanes()) {
                    if (lane.ok()) {
                        ok++;
                    }
                }
            }
            statusLabel.setText(ok == 0
                    ? "Compared 0/" + n + " solvers — every solver failed."
                    : "Compared " + ok + "/" + n
                            + " solvers — overlapping routes are consensus.");
            redraw();
            canvas.requestFocus();
            busy(false);
        });
        task.setOnFailed(e -> {
            allToggle.setSelected(false);
            fail(DesktopWork.describeFailure("Compare", task.getException()));
        });
        run(task, "Comparing every solver…");
    }

    /** Wired from the FXML Hunt checkbox. Same gold coins as the web Tour button. */
    @FXML
    public void onHunt() {
        if (huntToggle == null || !huntToggle.isSelected()) {
            currentHunt = null;
            huntGot.clear();
            redraw();
            return;
        }
        if (current == null) {
            huntToggle.setSelected(false);
            statusLabel.setText("Generate a maze first, then check Hunt.");
            return;
        }
        if (fogOn()) {
            huntToggle.setSelected(false);
            statusLabel.setText("Fog hides the hunt — uncheck Fog to place coins.");
            return;
        }
        stopPathReveal();
        currentPath = null;
        solvedPath = null;
        currentExpansions = null;
        solvedExpansions = null;
        clearRace();
        clearTheory();
        clearCompare();
        clearFollow();
        huntToggle.setSelected(true);
        huntGot.clear();
        var grid = current.grid();
        Task<DesktopPaint.Hunt> task = new Task<>() {
            @Override
            protected DesktopPaint.Hunt call() throws Exception {
                return work.huntJob(grid).call();
            }
        };
        task.setOnSucceeded(e -> {
            currentHunt = task.getValue();
            if (currentHunt == null || !currentHunt.feasible()) {
                statusLabel.setText("Hunt — those coins are not all reachable.");
            } else {
                statusLabel.setText("Hunt — collect " + currentHunt.waypoints().size()
                        + " coins then the goal. Optimal tour "
                        + currentHunt.optimalCost() + " steps.");
            }
            playerPos = current.metadata().start();
            resetWalk(playerPos);
            reachedGoal = false;
            redraw();
            canvas.requestFocus();
            busy(false);
        });
        task.setOnFailed(e -> {
            huntToggle.setSelected(false);
            fail(DesktopWork.describeFailure("Hunt", task.getException()));
        });
        run(task, "Placing the hunt…");
    }

    /** Wired from the FXML Race checkbox. Selected solver vs a rival, same arena as the web. */
    @FXML
    public void onRace() {
        if (raceToggle == null || !raceToggle.isSelected()) {
            currentRace = null;
            stopPathReveal();
            redraw();
            return;
        }
        if (current == null) {
            raceToggle.setSelected(false);
            statusLabel.setText("Generate a maze first, then check Race.");
            return;
        }
        if (fogOn()) {
            raceToggle.setSelected(false);
            statusLabel.setText("Fog hides the arena — uncheck Fog to race.");
            return;
        }
        String firstId = solverChoice.getValue();
        String secondId = DesktopWork.rivalOf(firstId, solverChoice.getItems());
        if (firstId == null || firstId.isBlank() || secondId == null) {
            raceToggle.setSelected(false);
            statusLabel.setText("Need two solvers to race.");
            return;
        }
        stopPathReveal();
        currentPath = null;
        solvedPath = null;
        currentExpansions = null;
        solvedExpansions = null;
        clearHunt();
        clearTheory();
        clearCompare();
        clearFollow();
        raceToggle.setSelected(true);
        var grid = current.grid();
        var mazeId = current.metadata().id();
        Task<DesktopPaint.Race> task = new Task<>() {
            @Override
            protected DesktopPaint.Race call() throws Exception {
                return work.raceJob(firstId, secondId, grid, mazeId).call();
            }
        };
        task.setOnSucceeded(e -> {
            currentRace = task.getValue();
            startRaceReveal();
            canvas.requestFocus();
            busy(false);
        });
        task.setOnFailed(e -> {
            raceToggle.setSelected(false);
            fail(DesktopWork.describeFailure("Race", task.getException()));
        });
        run(task, "Racing " + firstId + " vs " + secondId + "…");
    }

    private void clearLens() {
        currentLens = null;
        if (lensChoice != null && lensChoice.getValue() != LensPick.OFF) {
            lensChoice.getSelectionModel().select(LensPick.OFF);
        }
    }

    /** Wired from the FXML lens combo. Same three bands as the web Heuristic lens button. */
    @FXML
    public void onLens() {
        LensPick pick = lensChoice == null ? LensPick.OFF : lensChoice.getValue();
        if (pick == null || pick == LensPick.OFF || pick.heuristic == null) {
            currentLens = null;
            if (current != null) {
                redraw();
            }
            return;
        }
        if (current == null) {
            lensChoice.getSelectionModel().select(LensPick.OFF);
            statusLabel.setText("Generate a maze first, then pick a lens.");
            return;
        }
        if (fogOn()) {
            lensChoice.getSelectionModel().select(LensPick.OFF);
            statusLabel.setText("Fog hides the lens — uncheck Fog to see the bands.");
            return;
        }
        clearGhost();
        clearField();
        var mazeId = current.metadata().id();
        var which = pick.heuristic;
        Task<DesktopPaint.LensWash> task = new Task<>() {
            @Override
            protected DesktopPaint.LensWash call() throws Exception {
                return work.lensJob(mazeId, which).call();
            }
        };
        task.setOnSucceeded(e -> {
            currentLens = task.getValue();
            if (currentLens == null) {
                statusLabel.setText("Lens — no maze on the board.");
            } else {
                String opt = currentLens.routeOptimal() ? "optimal" : "not optimal";
                statusLabel.setText("Lens " + pick.label + " — must " + currentLens.mustExpand()
                        + " · tie " + currentLens.tie() + " · never " + currentLens.never()
                        + " · A* expanded " + currentLens.actualExpansions()
                        + " · route " + currentLens.routeLength() + " (" + opt + ").");
            }
            redraw();
            canvas.requestFocus();
            busy(false);
        });
        task.setOnFailed(e -> {
            if (lensChoice != null) {
                lensChoice.getSelectionModel().select(LensPick.OFF);
            }
            fail(DesktopWork.describeFailure("Lens", task.getException()));
        });
        run(task, "Shading the heuristic lens…");
    }

    /** Wired from the FXML Safe checkbox. Same mint discs as the web Place sanctuaries button. */
    @FXML
    public void onSanctuaries() {
        if (sanctuaryToggle == null || !sanctuaryToggle.isSelected()) {
            currentSanctuaries = null;
            redraw();
            return;
        }
        if (current == null) {
            sanctuaryToggle.setSelected(false);
            statusLabel.setText("Generate a maze first, then check Safe.");
            return;
        }
        if (fogOn()) {
            sanctuaryToggle.setSelected(false);
            statusLabel.setText("Fog hides the sanctuaries — uncheck Fog to place them.");
            return;
        }
        clearGhost();
        var grid = current.grid();
        Task<DesktopPaint.Sanctuaries> task = new Task<>() {
            @Override
            protected DesktopPaint.Sanctuaries call() throws Exception {
                return work.sanctuariesJob(grid).call();
            }
        };
        task.setOnSucceeded(e -> {
            currentSanctuaries = task.getValue();
            int n = currentSanctuaries == null || currentSanctuaries.placements() == null
                    ? 0 : currentSanctuaries.placements().size();
            int radius = currentSanctuaries == null ? 0 : currentSanctuaries.coveringRadius();
            statusLabel.setText(n + " sanctuaries · covering radius " + radius + ".");
            redraw();
            canvas.requestFocus();
            busy(false);
        });
        task.setOnFailed(e -> {
            sanctuaryToggle.setSelected(false);
            fail(DesktopWork.describeFailure("Sanctuaries", task.getException()));
        });
        run(task, "Placing sanctuaries…");
    }

    /** Wired from the FXML Long checkbox. Same gold walk as the web Hardest button. */
    @FXML
    public void onHardest() {
        if (hardestToggle == null || !hardestToggle.isSelected()) {
            currentHardest = null;
            redraw();
            return;
        }
        if (current == null) {
            hardestToggle.setSelected(false);
            statusLabel.setText("Generate a maze first, then check Long.");
            return;
        }
        if (fogOn()) {
            hardestToggle.setSelected(false);
            statusLabel.setText("Fog hides the hardest route — uncheck Fog to search.");
            return;
        }
        clearGhost();
        clearHunt();
        var grid = current.grid();
        Task<LongestPath.LongPath> task = new Task<>() {
            @Override
            protected LongestPath.LongPath call() throws Exception {
                return work.hardestJob(grid).call();
            }
        };
        task.setOnSucceeded(e -> {
            currentHardest = task.getValue();
            int n = currentHardest == null || currentHardest.path() == null
                    ? 0 : currentHardest.path().size();
            String bound = currentHardest != null && currentHardest.exact()
                    ? "exact" : "lower bound";
            statusLabel.setText("Hardest route — " + n + " cells (" + bound + ").");
            redraw();
            canvas.requestFocus();
            busy(false);
        });
        task.setOnFailed(e -> {
            hardestToggle.setSelected(false);
            fail(DesktopWork.describeFailure("Hardest", task.getException()));
        });
        run(task, "Searching for the hardest route…");
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
        clearGhost();
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
            currentExpansions = null;
            solvedExpansions = null;
            clearRace();
            clearHunt();
            clearCompare();
            clearFollow();
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
        Point from = playerPos;
        playerPos = step.position();
        work.occupy(current.metadata().id(), from, playerPos);
        rememberWalk(playerPos);
        if (currentHunt != null) {
            noteHunt(playerPos, step.reachedGoal());
        } else if (step.reachedGoal()) {
            reachedGoal = true;
            finishGhostRace();
        }
        if (step.reachedGoal()) {
            reachedGoal = true;
        }
        redraw();
    }

    private void noteHunt(Point at, boolean atGoal) {
        if (currentHunt.waypoints().contains(at)) {
            huntGot.add(at);
        }
        int got = huntGot.size();
        int total = currentHunt.waypoints().size();
        int walked = Math.max(0, playerWalk.size() - 1);
        if (atGoal && got == total) {
            statusLabel.setText("Tour complete in " + walked + " steps; optimal is "
                    + currentHunt.optimalCost() + ".");
            return;
        }
        if (atGoal) {
            int missed = total - got;
            statusLabel.setText("Reached the goal — " + missed
                    + (missed == 1 ? " coin" : " coins") + " still out.");
            return;
        }
        if (got == total) {
            statusLabel.setText("All coins collected — reach the goal (" + walked
                    + " steps, optimal " + currentHunt.optimalCost() + ").");
            return;
        }
        statusLabel.setText("Hunt " + got + "/" + total + " · " + walked
                + " steps · optimal " + currentHunt.optimalCost() + ".");
    }

    // ---------- rendering ----------

    private void stopPathReveal() {
        if (pathReveal != null) {
            pathReveal.stop();
            pathReveal = null;
        }
    }

    /**
     * Two-act reveal — search wash, then the route. Same timing as
     * {@code solve.js} {@code search}: BFS floods, A* beelines, then the ribbon.
     */
    private void startSolveReveal() {
        stopPathReveal();
        List<Point> search = solvedExpansions == null ? List.of() : solvedExpansions;
        List<Point> full = solvedPath == null ? List.of() : solvedPath;
        currentExpansions = List.of();
        currentPath = List.of();
        long searchNs = DesktopPaint.searchRevealMs(search.size()) * 1_000_000L;
        long pathNs = DesktopPaint.pathRevealMs(full.size()) * 1_000_000L;
        if (search.isEmpty() && full.isEmpty()) {
            redraw();
            return;
        }
        if (search.isEmpty()) {
            currentExpansions = List.of();
        }
        long started = System.nanoTime();
        pathReveal = new AnimationTimer() {
            @Override
            public void handle(long now) {
                long t = System.nanoTime() - started;
                double searchP = searchNs == 0 ? 1.0 : Math.min(1.0, t / (double) searchNs);
                currentExpansions = search.isEmpty()
                        ? List.of() : DesktopPaint.pathPrefix(search, searchP);
                double pathP = searchNs == 0
                        ? Math.min(1.0, t / (double) pathNs)
                        : Math.max(0.0, Math.min(1.0, (t - searchNs) / (double) pathNs));
                currentPath = full.isEmpty() ? List.of() : DesktopPaint.pathPrefix(full, pathP);
                redraw();
                if (searchP >= 1 && pathP >= 1) {
                    currentExpansions = search;
                    currentPath = full;
                    stopPathReveal();
                }
            }
        };
        pathReveal.start();
    }

    /**
     * Equal expansions-per-second, then each route. Same timing as
     * {@code solve.js} {@code raceTick} — the leaner search finishes first.
     */
    private void startRaceReveal() {
        stopPathReveal();
        DesktopPaint.Race race = currentRace;
        if (race == null || race.first() == null || race.second() == null) {
            redraw();
            return;
        }
        raceFrontA = 0;
        racePathA = 0;
        raceFrontB = 0;
        racePathB = 0;
        int maxN = Math.max(1, Math.max(race.first().expansions().size(),
                race.second().expansions().size()));
        double rate = DesktopPaint.raceRate(maxN);
        long pathANs = DesktopPaint.pathRevealMs(race.first().path().size()) * 1_000_000L;
        long pathBNs = DesktopPaint.pathRevealMs(race.second().path().size()) * 1_000_000L;
        long started = System.nanoTime();
        pathReveal = new AnimationTimer() {
            @Override
            public void handle(long now) {
                double t = (System.nanoTime() - started) / 1_000_000_000.0;
                raceFrontA = frontAt(race.first().expansions().size(), t, rate);
                raceFrontB = frontAt(race.second().expansions().size(), t, rate);
                racePathA = pathAt(race.first().expansions().size(), t, rate, pathANs);
                racePathB = pathAt(race.second().expansions().size(), t, rate, pathBNs);
                redraw();
                if (raceFrontA >= 1 && raceFrontB >= 1 && racePathA >= 1 && racePathB >= 1) {
                    raceFrontA = 1;
                    raceFrontB = 1;
                    racePathA = 1;
                    racePathB = 1;
                    statusLabel.setText(raceSummary(race));
                    stopPathReveal();
                }
            }
        };
        pathReveal.start();
    }

    private static double frontAt(int expansions, double seconds, double rate) {
        if (expansions <= 0) {
            return 1;
        }
        return Math.min(1.0, (seconds * rate) / expansions);
    }

    private static double pathAt(int expansions, double seconds, double rate, long pathNs) {
        double front = frontAt(expansions, seconds, rate);
        if (front < 1 || pathNs <= 0) {
            return front >= 1 ? 1 : 0;
        }
        double doneAt = expansions / rate;
        return Math.min(1.0, ((seconds - doneAt) * 1_000_000_000.0) / pathNs);
    }

    private static String raceSummary(DesktopPaint.Race race) {
        int a = race.first().expansions().size();
        int b = race.second().expansions().size();
        String winner = a == b ? "tied on work"
                : (a < b ? race.first().id() : race.second().id()) + " wins";
        return "Arena — " + race.first().id() + " " + a + " expansions vs "
                + race.second().id() + " " + b + ". " + winner + ".";
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

        if (currentLens != null && currentLens.bands() != null) {
            int[][] bands = currentLens.bands();
            for (int r = 0; r < bands.length; r++) {
                for (int c = 0; c < bands[r].length; c++) {
                    String color = DesktopPaint.lensColor(bands[r][c]);
                    if (color == null) {
                        continue;
                    }
                    g.setFill(Color.web(color));
                    g.setGlobalAlpha(DesktopPaint.lensAlpha(bands[r][c]));
                    g.fillRect(layout.x(2 * c + 1), layout.y(2 * r + 1),
                            layout.w(2 * c + 1), layout.h(2 * r + 1));
                }
            }
            g.setFill(Color.web(DesktopPaint.LENS_COLORS[2]));
            g.setGlobalAlpha(DesktopPaint.LENS_OPENING_ALPHA);
            for (DesktopPaint.TileRect tile : DesktopPaint.lensOpenings(bands, tiles)) {
                g.fillRect(layout.x(tile.tileCol()), layout.y(tile.tileRow()),
                        layout.w(tile.tileCol()), layout.h(tile.tileRow()));
            }
            g.setGlobalAlpha(1);
        }

        // ---- 2) recorded search wash, player walk, then solve-path overlay ----
        if (currentExpansions != null && !currentExpansions.isEmpty() && theme != null) {
            g.setFill(theme.path());
            g.setGlobalAlpha(DesktopPaint.EXPANSION_ALPHA);
            for (DesktopPaint.TileRect tile : DesktopPaint.expansionCells(currentExpansions)) {
                g.fillRect(layout.x(tile.tileCol()), layout.y(tile.tileRow()),
                        layout.w(tile.tileCol()), layout.h(tile.tileRow()));
            }
            for (DesktopPaint.TileRect tile : DesktopPaint.expansionOpenings(
                    currentExpansions, tiles)) {
                g.fillRect(layout.x(tile.tileCol()), layout.y(tile.tileRow()),
                        layout.w(tile.tileCol()), layout.h(tile.tileRow()));
            }
            g.setGlobalAlpha(DesktopPaint.EXPANSION_FRONT_ALPHA);
            for (DesktopPaint.TileRect tile : DesktopPaint.expansionCells(
                    DesktopPaint.expansionFront(currentExpansions))) {
                g.fillRect(layout.x(tile.tileCol()), layout.y(tile.tileRow()),
                        layout.w(tile.tileCol()), layout.h(tile.tileRow()));
            }
            g.setGlobalAlpha(1);
        }
        if (currentRace != null) {
            paintRaceLane(g, layout, tiles, currentRace.first(), raceFrontA, racePathA,
                    DesktopPaint.RACE_PATH_A);
            paintRaceLane(g, layout, tiles, currentRace.second(), raceFrontB, racePathB,
                    DesktopPaint.RACE_PATH_B);
        }
        if (currentCompare != null && currentCompare.lanes() != null) {
            for (DesktopPaint.CompareLane lane : currentCompare.lanes()) {
                if (lane.path() == null || lane.path().isEmpty()) {
                    continue;
                }
                g.setFill(Color.web(lane.color()));
                g.setGlobalAlpha(DesktopPaint.COMPARE_ALPHA);
                for (DesktopPaint.TileRect tile : DesktopPaint.walkOverlay(lane.path())) {
                    g.fillRect(layout.x(tile.tileCol()), layout.y(tile.tileRow()),
                            layout.w(tile.tileCol()), layout.h(tile.tileRow()));
                }
            }
            g.setGlobalAlpha(1);
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
        List<Point> ghostWalk = ghostWalkNow();
        if (!ghostWalk.isEmpty()) {
            g.setGlobalAlpha(DesktopPaint.GHOST_WALK_ALPHA);
            g.setFill(Color.web(DesktopPaint.GHOST));
            for (DesktopPaint.TileRect tile : DesktopPaint.walkOverlay(ghostWalk)) {
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

        if (currentSanctuaries != null && currentSanctuaries.placements() != null) {
            g.setFill(Color.web(DesktopPaint.SANCTUARY));
            for (Point safe : currentSanctuaries.placements()) {
                DesktopPaint.Marker disc = DesktopPaint.sanctuaryMarker(layout, safe);
                if (disc == null) {
                    continue;
                }
                g.fillOval(disc.x(), disc.y(), disc.size(), disc.size());
            }
            paintRing(g, DesktopPaint.worstServedRing(layout, currentSanctuaries.worstServed()),
                    Color.web(DesktopPaint.WORST_SERVED));
        }

        if (currentHardest != null && currentHardest.path() != null
                && !currentHardest.path().isEmpty()) {
            g.setGlobalAlpha(DesktopPaint.HARDEST_ALPHA);
            g.setFill(Color.web(DesktopPaint.HARDEST));
            for (DesktopPaint.TileRect tile : DesktopPaint.walkOverlay(currentHardest.path())) {
                g.fillRect(layout.x(tile.tileCol()), layout.y(tile.tileRow()),
                        layout.w(tile.tileCol()), layout.h(tile.tileRow()));
            }
            g.setGlobalAlpha(1);
        }

        if (currentHunt != null && currentHunt.path() != null && !currentHunt.path().isEmpty()) {
            g.setGlobalAlpha(DesktopPaint.TOUR_ALPHA);
            g.setFill(Color.web(DesktopPaint.TOUR));
            for (DesktopPaint.TileRect tile : DesktopPaint.walkOverlay(currentHunt.path())) {
                g.fillRect(layout.x(tile.tileCol()), layout.y(tile.tileRow()),
                        layout.w(tile.tileCol()), layout.h(tile.tileRow()));
            }
            g.setGlobalAlpha(1);
        }
        if (currentHunt != null && currentHunt.waypoints() != null) {
            for (Point coin : currentHunt.waypoints()) {
                paintDiamond(g, DesktopPaint.waypointDiamond(layout, coin), huntGot.contains(coin));
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
        paintGhostDisc(g, layout, DesktopPaint.ghostHead(ghostWalkNow()));
        if (reachedGoal) {
            paintRing(g, DesktopPaint.victoryRing(layout, current.metadata().goal()),
                    Color.web(DesktopPaint.VICTORY_GOLD));
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
                        && !currentCuts.chokepoints().isEmpty(),
                currentHardest != null && currentHardest.path() != null
                        && !currentHardest.path().isEmpty(),
                currentSanctuaries != null && currentSanctuaries.placements() != null
                        && !currentSanctuaries.placements().isEmpty(),
                currentLens != null && currentLens.bands() != null,
                currentRace != null,
                currentHunt != null && currentHunt.waypoints() != null
                        && !currentHunt.waypoints().isEmpty(),
                !ghostWalkNow().isEmpty(),
                currentCompare != null && currentCompare.lanes() != null
                        && !currentCompare.lanes().isEmpty());
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
        showLegendKey(legendHardest, keys.contains("hardest"));
        showLegendKey(legendSanctuary, keys.contains("sanctuary"));
        showLegendKey(legendLens, keys.contains("lens"));
        showLegendKey(legendRace, keys.contains("race"));
        showLegendKey(legendWaypoint, keys.contains("waypoint"));
        showLegendKey(legendGhost, keys.contains("ghost"));
        showLegendKey(legendCompare, keys.contains("compare"));
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
            paintRing(g, DesktopPaint.victoryRing(layout, current.metadata().goal()),
                    Color.web(DesktopPaint.VICTORY_GOLD));
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
        walkMoves.clear();
        walkStartedNs = System.nanoTime();
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
        if (walkMoves.size() >= GameSession.MAX_TRAIL) {
            return;
        }
        long tMs = Math.max(0L, (System.nanoTime() - walkStartedNs) / 1_000_000L);
        walkMoves.add(new GameSession.TimedMove(cell, tMs));
    }

    private void finishGhostRace() {
        DesktopWork.GhostTape racing = ghostTape;
        if (current != null && !walkMoves.isEmpty()) {
            work.challengeGhost(current.metadata().id(), "you",
                    current.metadata().start(), walkMoves);
        }
        stopGhostWatch();
        ghostDone = true;
        if (racing != null && !walkMoves.isEmpty()) {
            long mine = walkMoves.get(walkMoves.size() - 1).tMs();
            long theirs = racing.elapsedMs();
            if (mine < theirs) {
                statusLabel.setText(String.format(
                        "Reached the goal — you BEAT the ghost by %.1fs!",
                        (theirs - mine) / 1000.0));
            } else {
                statusLabel.setText(String.format(
                        "Reached the goal — the ghost was %.1fs faster.",
                        (mine - theirs) / 1000.0));
            }
            return;
        }
        statusLabel.setText("Reached the goal! Reset to race the ghost.");
    }

    private void paintRaceLane(GraphicsContext g, DesktopPaint.Layout layout,
                               TileType[][] tiles, DesktopPaint.RaceLane lane,
                               double front, double pathProg, double pathAlpha) {
        if (lane == null) {
            return;
        }
        List<Point> shown = DesktopPaint.pathPrefix(lane.expansions(), front);
        g.setFill(Color.web(lane.color()));
        g.setGlobalAlpha(DesktopPaint.RACE_WASH);
        for (DesktopPaint.TileRect tile : DesktopPaint.expansionCells(shown)) {
            g.fillRect(layout.x(tile.tileCol()), layout.y(tile.tileRow()),
                    layout.w(tile.tileCol()), layout.h(tile.tileRow()));
        }
        for (DesktopPaint.TileRect tile : DesktopPaint.expansionOpenings(shown, tiles)) {
            g.fillRect(layout.x(tile.tileCol()), layout.y(tile.tileRow()),
                    layout.w(tile.tileCol()), layout.h(tile.tileRow()));
        }
        g.setGlobalAlpha(DesktopPaint.RACE_FRONT_ALPHA);
        for (DesktopPaint.TileRect tile : DesktopPaint.expansionCells(
                DesktopPaint.raceFront(shown))) {
            g.fillRect(layout.x(tile.tileCol()), layout.y(tile.tileRow()),
                    layout.w(tile.tileCol()), layout.h(tile.tileRow()));
        }
        g.setGlobalAlpha(1);
        if (pathProg > 0 && !lane.path().isEmpty()) {
            List<Point> ribbon = DesktopPaint.pathPrefix(lane.path(), pathProg);
            g.setGlobalAlpha(pathAlpha);
            for (DesktopPaint.TileRect tile : DesktopPaint.walkOverlay(ribbon)) {
                g.fillRect(layout.x(tile.tileCol()), layout.y(tile.tileRow()),
                        layout.w(tile.tileCol()), layout.h(tile.tileRow()));
            }
            g.setGlobalAlpha(1);
            paintDisc(g, DesktopPaint.raceHeadMarker(layout, ribbon), Color.web(lane.color()));
        }
    }

    private static void paintDiamond(GraphicsContext g, DesktopPaint.Diamond diamond,
                                     boolean collected) {
        if (diamond == null) {
            return;
        }
        double cx = diamond.cx();
        double cy = diamond.cy();
        double r = diamond.radius();
        double[] xs = {cx, cx + r, cx, cx - r};
        double[] ys = {cy - r, cy, cy + r, cy};
        if (collected) {
            g.setStroke(Color.web(DesktopPaint.WAYPOINT_GOT));
            g.setLineWidth(diamond.stroke());
            g.strokePolygon(xs, ys, 4);
        } else {
            g.setFill(Color.web(DesktopPaint.WAYPOINT));
            g.fillPolygon(xs, ys, 4);
        }
    }

    private static void paintGhostDisc(GraphicsContext g, DesktopPaint.Layout layout, Point cell) {
        DesktopPaint.Marker mark = DesktopPaint.ghostMarker(layout, cell);
        if (mark == null) {
            return;
        }
        Color ink = Color.web(DesktopPaint.GHOST);
        g.setGlobalAlpha(DesktopPaint.GHOST_DISC_ALPHA);
        g.setFill(ink);
        g.fillOval(mark.x(), mark.y(), mark.size(), mark.size());
        g.setGlobalAlpha(1);
        g.setStroke(ink);
        g.setLineWidth(1);
        g.strokeOval(mark.x(), mark.y(), mark.size(), mark.size());
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

    private static void paintRing(GraphicsContext g, DesktopPaint.Ring ring, Color color) {
        if (ring == null || color == null) {
            return;
        }
        g.setStroke(color);
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
