// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.api.dto.Hotspot;
import com.daedalus.engine.MazeGrid;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.MazeSolverService;
import com.daedalus.solver.SolverBudgetExceededException;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.UUID;
import java.util.concurrent.Callable;

/**
 * The two long-running desktop operations, as plain {@link Callable}s that know nothing about
 * JavaFX.
 *
 * <h3>Why this class exists</h3>
 *
 * <p>{@link MainController} used to call the generation and solver services inline from its
 * {@code @FXML} handlers, on the JavaFX Application Thread, under a documented assumption:
 * <em>"Generation and solve are fast enough at the Spinner-bounded sizes (≤ 128² = 16 384 cells)
 * that we don't background them; if a later change pushes that into the multi-second range, wrap
 * the calls in a Task."</em>
 *
 * <p>Twenty features later, an audit re-measured that assumption at the spinner's own maximum.
 * The trigger condition it named had been met three times over:
 *
 * <pre>
 *   hunt-and-kill generate, 128x128    1101 ms
 *   IDA* solve, perfect 128x128        1783 ms   (spends its node budget, then refuses)
 *   IDA* solve, dungeon 128x128        1518 ms   (same)
 * </pre>
 *
 * <p>Every one of those is the window frozen — no repaint, no input, and on some desktops the
 * "application is not responding" overlay. Nobody had done anything wrong: the assumption was
 * true when written, the code that invalidated it lives in another module, and no test watches
 * wall-clock. That is exactly the shape of assumption worth re-measuring rather than re-reading.
 *
 * <p><b>Why plain Callables and not Tasks.</b> The desktop module deliberately has no TestFX or
 * Monocle — the existing tests say so outright, and pulling a headless toolkit in to cover glue
 * would be a poor trade. A {@code javafx.concurrent.Task} cannot be exercised without an
 * initialised toolkit, because its state transitions go through {@code Platform.runLater}. Plain
 * callables can be run and asserted on any thread, so the work is testable here and
 * {@link MainController} keeps only the thin wrapper that genuinely needs JavaFX.
 */
@Component
public class DesktopWork {

    private final MazeGenerationService generation;
    private final MazeSolverService solving;

    public DesktopWork(MazeGenerationService generation, MazeSolverService solving) {
        this.generation = generation;
        this.solving = solving;
    }

    /** Generate a maze off the FX thread. */
    public Callable<MazeGenerationService.Cached> generateJob(
            String generatorId, int rows, int cols, long seed) {
        return generateJob(generatorId, rows, cols, seed, null);
    }

    /** Weighted generate — {@code null} or empty hotspots stay the uniform-cost contract. */
    public Callable<MazeGenerationService.Cached> generateJob(
            String generatorId, int rows, int cols, long seed,
            List<Hotspot> hotspots) {
        return () -> generation.generate(generatorId, rows, cols, seed, hotspots);
    }

    /** Solve a maze off the FX thread. */
    public Callable<MazeSolverService.Result> solveJob(
            String solverId, MazeGrid grid, UUID mazeId) {
        return () -> solving.solve(solverId, grid, mazeId);
    }

    /**
     * Turn a failure into something worth putting in a status bar.
     *
     * <p>A solver giving up on its node budget is not a crash and should not read like one: it
     * is the cost guard doing its job, and the exception already carries a message written to be
     * understood outside the API layer. Anything else keeps its class name, because an unexpected
     * failure that pretends to be routine is how a bug goes unreported.
     */
    public static String describeFailure(String action, Throwable failure) {
        Throwable cause = failure instanceof java.util.concurrent.ExecutionException
                ? failure.getCause() : failure;
        if (cause instanceof SolverBudgetExceededException budget) {
            return budget.getMessage();
        }
        String message = cause == null ? null : cause.getMessage();
        return action + " failed: "
                + (message == null || message.isBlank()
                        ? cause == null ? "unknown error" : cause.getClass().getSimpleName()
                        : message);
    }
}
