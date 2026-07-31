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

    /**
     * Adds a generator. <b>First registration wins</b> — see
     * {@link com.daedalus.engine.DuplicateAlgorithmException} for why a collision is refused
     * rather than logged. Built-ins register from the constructor, so no plugin can displace one.
     *
     * @throws com.daedalus.engine.DuplicateAlgorithmException if the id is already taken
     */
    public void register(MazeGenerator gen) {
        MazeGenerator incumbent = generators.putIfAbsent(gen.id(), gen);
        // No exemption for re-registering the identical instance. That looked like a kindness
        // for a double-boot, and nobody could name the path that reaches it — an exception whose
        // triggering case is hypothetical is permission granted for free. One rule: a taken id
        // is taken. If something registers twice, that is worth failing over.
        if (incumbent != null) {
            throw new com.daedalus.engine.DuplicateAlgorithmException(
                    "generator", gen.id(), incumbent.getClass(), gen.getClass());
        }
    }

    public Optional<MazeGenerator> find(String id) {
        return Optional.ofNullable(generators.get(id));
    }

    /**
     * @throws com.daedalus.engine.UnknownAlgorithmException if nothing is registered under
     *         {@code id}. A subtype of {@link NoSuchElementException}, so this is source- and
     *         behaviour-compatible with what it used to throw; the REST layer needs the distinct
     *         type to answer 404 for a caller's typo without also swallowing every genuine
     *         internal {@code NoSuchElementException} as a 404.
     */
    public MazeGenerator require(String id) {
        return find(id).orElseThrow(() -> new com.daedalus.engine.UnknownAlgorithmException(
                "generator", id, generators.keySet().stream().sorted().toList()));
    }

    public Collection<MazeGenerator> all() {
        return Collections.unmodifiableCollection(generators.values());
    }

    public List<AlgorithmDescriptor> descriptors() {
        return generators.values().stream().map(MazeGenerator::descriptor).toList();
    }

    public int size() { return generators.size(); }
}
