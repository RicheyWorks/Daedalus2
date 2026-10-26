// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AlgorithmRegistry;
import com.daedalus.engine.MazeGenerator;
import com.daedalus.model.AlgorithmDescriptor;

import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.Set;

/**
 * Central registry for all known maze generators. Built-ins come from {@code AlgorithmConfig};
 * plugins register additional generators through {@code MazePlugin#registerAlgorithms}.
 *
 * <p>The map, collision guard, and built-in refusal live on {@link AlgorithmRegistry} so
 * they cannot drift from {@code SolverRegistry}.
 */
public class GeneratorRegistry {

    private final AlgorithmRegistry<MazeGenerator> inner;

    public GeneratorRegistry(List<MazeGenerator> builtIn) {
        this.inner = new AlgorithmRegistry<>(builtIn, "generator",
                MazeGenerator::id, MazeGenerator::descriptor);
    }

    /**
     * Adds a generator. First registration wins — see
     * {@link com.daedalus.engine.DuplicateAlgorithmException}.
     */
    public void register(MazeGenerator gen) {
        inner.register(gen);
    }

    /**
     * Removes a generator contributed by a plugin. Built-ins are refused.
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

    public Optional<MazeGenerator> find(String id) {
        return inner.find(id);
    }

    public MazeGenerator require(String id) {
        return inner.require(id);
    }

    public Collection<MazeGenerator> all() {
        return inner.all();
    }

    public List<AlgorithmDescriptor> descriptors() {
        return inner.descriptors();
    }

    public int size() {
        return inner.size();
    }
}
