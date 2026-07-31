// SPDX-License-Identifier: MIT

package com.daedalus.solver.solvers;

import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.solver.MazeSolver;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Central registry for all known solvers. Built-ins come from {@code AlgorithmConfig};
 * plugins register additional solvers through {@code MazePlugin#registerAlgorithms}.
 *
 * <p>Plain Java — no Spring annotations. The registry is wired into the Spring context by
 * {@code AlgorithmConfig} in daedalus-server (via an {@code @Bean} factory method); a
 * non-Spring host can construct it directly with {@code new SolverRegistry(solvers)}.
 */
public class SolverRegistry {

    private final Map<String, MazeSolver> solvers = new ConcurrentHashMap<>();

    public SolverRegistry(List<MazeSolver> builtIn) {
        builtIn.forEach(this::register);
    }

    /**
     * Adds a solver. First registration wins; see
     * {@link com.daedalus.engine.DuplicateAlgorithmException}.
     *
     * @throws com.daedalus.engine.DuplicateAlgorithmException if the id is already taken
     */
    public void register(MazeSolver s) {
        MazeSolver incumbent = solvers.putIfAbsent(s.id(), s);
        // No exemption for re-registering the identical instance. That looked like a kindness
        // for a double-boot, and nobody could name the path that reaches it — an exception whose
        // triggering case is hypothetical is permission granted for free. One rule: a taken id
        // is taken. If something registers twice, that is worth failing over.
        if (incumbent != null) {
            throw new com.daedalus.engine.DuplicateAlgorithmException(
                    "solver", s.id(), incumbent.getClass(), s.getClass());
        }
    }

    public Optional<MazeSolver> find(String id) {
        return Optional.ofNullable(solvers.get(id));
    }

    /**
     * @throws com.daedalus.engine.UnknownAlgorithmException if nothing is registered under
     *         {@code id} — see {@code GeneratorRegistry#require} for why this is its own type
     *         rather than a bare {@link NoSuchElementException}.
     */
    public MazeSolver require(String id) {
        return find(id).orElseThrow(() -> new com.daedalus.engine.UnknownAlgorithmException(
                "solver", id, solvers.keySet().stream().sorted().toList()));
    }

    public Collection<MazeSolver> all() {
        return Collections.unmodifiableCollection(solvers.values());
    }

    public List<AlgorithmDescriptor> descriptors() {
        return solvers.values().stream().map(MazeSolver::descriptor).toList();
    }

    public int size() { return solvers.size(); }
}
