// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.generators.*;
import com.daedalus.solver.MazeSolver;
import com.daedalus.solver.solvers.*;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;

/**
 * Strategy registration.
 *
 * <p>Every built-in generator and solver is a Spring bean keyed by its {@code id()}.
 * Plugins can contribute additional implementations via {@code MazePlugin#registerAlgorithms}
 * and they show up in the same registries.
 *
 * <p>Mirrors the CSRBT pattern of swappable algorithms — the engine never references concrete
 * classes, only the {@code MazeGenerator} / {@code MazeSolver} interfaces.
 *
 * <p><b>To add a new generator:</b> drop the class in {@code engine/generators/}, then add
 * one line to {@link #builtInGenerators()}. Same for solvers in {@link #builtInSolvers()}.
 * The registry, REST endpoints, and UI dropdowns pick it up automatically.
 */
@Configuration
public class AlgorithmConfig {

    @Bean
    public List<MazeGenerator> builtInGenerators() {
        return List.of(
                new RecursiveBacktrackerGenerator(),
                new PrimsGenerator(),
                new KruskalsGenerator(),
                new BoruvkasGenerator(),
                new WilsonsGenerator(),
                new HuntAndKillGenerator(),
                new RecursiveDivisionGenerator(),
                new BinaryTreeGenerator(),
                new SidewinderGenerator(),
                new GrowingTreeGenerator(),
                new OldestPickGenerator(),
                new AldousBroderGenerator(),
                new EllersGenerator(),
                new KrakenGenerator(),
                new MortonCurveGenerator(),
                new HilbertCurveGenerator(),
                new LightningGenerator(),
                new TuringGenerator(),
                new GaussGenerator(),
                new ArchimedesGenerator()
        );
    }

    @Bean
    public List<MazeSolver> builtInSolvers() {
        return List.of(
                new BfsSolver(),
                new DfsSolver(),
                new AStarSolver(),
                new DijkstraSolver(),
                new DialSolver(),
                new BidirectionalSolver(),
                new IDAStarSolver(),
                new WallFollowerSolver(),
                new TremauxSolver(),
                new DeadEndFillingSolver()
        );
    }

    /**
     * Wire the GeneratorRegistry into the Spring context. The registry itself lives in
     * daedalus-core as a plain Java class (no Spring annotations); this @Bean factory
     * is the bridge that makes it a managed bean for the server module.
     */
    @Bean
    public GeneratorRegistry generatorRegistry(List<MazeGenerator> builtInGenerators) {
        return new GeneratorRegistry(builtInGenerators);
    }

    /**
     * Wire the SolverRegistry into the Spring context. Same pattern as
     * {@link #generatorRegistry(List)}.
     */
    @Bean
    public SolverRegistry solverRegistry(List<MazeSolver> builtInSolvers) {
        return new SolverRegistry(builtInSolvers);
    }
}
