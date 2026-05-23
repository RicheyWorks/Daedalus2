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

    public void register(MazeSolver s) { solvers.put(s.id(), s); }

    public Optional<MazeSolver> find(String id) {
        return Optional.ofNullable(solvers.get(id));
    }

    public MazeSolver require(String id) {
        return find(id).orElseThrow(() ->
                new NoSuchElementException("No solver registered with id: " + id));
    }

    public Collection<MazeSolver> all() {
        return Collections.unmodifiableCollection(solvers.values());
    }

    public List<AlgorithmDescriptor> descriptors() {
        return solvers.values().stream().map(MazeSolver::descriptor).toList();
    }

    public int size() { return solvers.size(); }
}
