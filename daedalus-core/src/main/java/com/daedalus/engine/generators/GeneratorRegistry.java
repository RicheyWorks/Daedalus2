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

    /** Ids present after construction. Permanent — {@link #unregister} refuses these. */
    private final Set<String> builtInIds;

    public GeneratorRegistry(List<MazeGenerator> builtIn) {
        builtIn.forEach(this::register);
        // Snapshotted after the built-ins register and never added to again: this is the set
        // generator ids that {@link #unregister} must refuse, so a plugin unload can never take
        // a shipped algorithm with it.
        this.builtInIds = Set.copyOf(generators.keySet());
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

    /**
     * Removes a generator contributed by a plugin. Built-ins are refused.
     *
     * <p>Added 2026-07-31 with the plugin-unload fix. Until then neither registry had any
     * removal path at all, so {@code PluginManager.shutdownAll()} closed a plugin's
     * {@code URLClassLoader} while the algorithms it contributed stayed in this map — a
     * "stopped" plugin's generator remained listed by {@code /api/v1/algorithms} and remained
     * callable, because closing a loader does not unload classes already loaded from it.
     *
     * <p>The refusal for built-ins is the whole reason this is not a plain {@code remove}.
     * A removal path reachable from plugin teardown is a removal path a buggy or hostile
     * teardown can point at {@code "recursive-backtracker"}, which would undo the collision
     * guard from the other direction: a plugin that cannot replace a built-in could otherwise
     * simply delete it.
     *
     * @param id the generator id to remove
     * @return {@code true} if something was removed
     * @throws IllegalArgumentException if {@code id} names a built-in
     */
    public boolean unregister(String id) {
        if (builtInIds.contains(id)) {
            throw new IllegalArgumentException(
                    "'" + id + "' is a built-in generator and cannot be unregistered. Only "
                            + "plugin-contributed algorithms can be removed.");
        }
        return generators.remove(id) != null;
    }

    /** Every registered id, for callers that need to diff the registry across an operation. */
    public Set<String> ids() {
        return Set.copyOf(generators.keySet());
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
