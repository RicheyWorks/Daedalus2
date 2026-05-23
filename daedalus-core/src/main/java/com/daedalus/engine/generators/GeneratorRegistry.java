// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.MazeGenerator;
import com.daedalus.model.AlgorithmDescriptor;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Central registry for all known maze generators. Built-ins come from {@code AlgorithmConfig};
 * plugins register additional generators through {@code MazePlugin#registerAlgorithms} which
 * calls {@link #register}.
 *
 * <p>Plain Java — no Spring annotations. The registry is wired into the Spring context by
 * {@code AlgorithmConfig} in daedalus-server (via an {@code @Bean} factory method); a
 * non-Spring host can construct it directly with {@code new GeneratorRegistry(generators)}.
 */
public class GeneratorRegistry {

    private final Map<String, MazeGenerator> generators = new ConcurrentHashMap<>();

    public GeneratorRegistry(List<MazeGenerator> builtIn) {
        builtIn.forEach(this::register);
    }

    public void register(MazeGenerator gen) {
        generators.put(gen.id(), gen);
    }

    public Optional<MazeGenerator> find(String id) {
        return Optional.ofNullable(generators.get(id));
    }

    public MazeGenerator require(String id) {
        return find(id).orElseThrow(() ->
                new NoSuchElementException("No generator registered with id: " + id));
    }

    public Collection<MazeGenerator> all() {
        return Collections.unmodifiableCollection(generators.values());
    }

    public List<AlgorithmDescriptor> descriptors() {
        return generators.values().stream().map(MazeGenerator::descriptor).toList();
    }

    public int size() { return generators.size(); }
}
