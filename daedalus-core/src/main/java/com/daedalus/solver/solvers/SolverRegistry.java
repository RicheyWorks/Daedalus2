// SPDX-License-Identifier: MIT

package com.daedalus.solver.solvers;

import com.daedalus.engine.AlgorithmRegistry;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.solver.MazeSolver;

import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.Set;

/**
 * Central registry for all known solvers. Built-ins come from {@code AlgorithmConfig};
 * plugins register additional solvers through {@code MazePlugin#registerAlgorithms}.
 *
 * <p>Delegates to {@link AlgorithmRegistry} so collision and unload rules stay
 * identical to {@code GeneratorRegistry}.
 */
public class SolverRegistry {

    private final AlgorithmRegistry<MazeSolver> inner;

    public SolverRegistry(List<MazeSolver> builtIn) {
        this.inner = new AlgorithmRegistry<>(builtIn, "solver",
                MazeSolver::id, MazeSolver::descriptor);
    }

    /**
     * Adds a solver. First registration wins; see
     * {@link com.daedalus.engine.DuplicateAlgorithmException}.
     */
    public void register(MazeSolver s) {
        inner.register(s);
    }

    /**
     * Removes a solver contributed by a plugin. Built-ins are refused.
     *
     * @return {@code true} if something was removed
     * @throws IllegalArgumentException if {@code id} names a built-in
     */
    public boolean unregister(String id) {
        return inner.unregister(id);
    }

    public Set<String> ids() {
        return inner.ids();
    }

    public Optional<MazeSolver> find(String id) {
        return inner.find(id);
    }

    public MazeSolver require(String id) {
        return inner.require(id);
    }

    public Collection<MazeSolver> all() {
        return inner.all();
    }

    public List<AlgorithmDescriptor> descriptors() {
        return inner.descriptors();
    }

    public int size() {
        return inner.size();
    }
}
