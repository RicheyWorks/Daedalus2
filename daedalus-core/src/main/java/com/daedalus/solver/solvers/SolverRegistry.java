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

    /** Ids present after construction. Permanent — {@link #unregister} refuses these. */
    private final Set<String> builtInIds;

    public SolverRegistry(List<MazeSolver> builtIn) {
        builtIn.forEach(this::register);
        // Snapshotted after the built-ins register and never added to again: this is the set
        // solver ids that {@link #unregister} must refuse, so a plugin unload can never take
        // a shipped algorithm with it.
        this.builtInIds = Set.copyOf(solvers.keySet());
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

    /**
     * Removes a solver contributed by a plugin. Built-ins are refused.
     *
     * <p>Added 2026-07-31 with the plugin-unload fix. Until then neither registry had any
     * removal path at all, so {@code PluginManager.shutdownAll()} closed a plugin's
     * {@code URLClassLoader} while the algorithms it contributed stayed in this map — a
     * "stopped" plugin's solver remained listed by {@code /api/v1/algorithms} and remained
     * callable, because closing a loader does not unload classes already loaded from it.
     *
     * <p>The refusal for built-ins is the whole reason this is not a plain {@code remove}.
     * A removal path reachable from plugin teardown is a removal path a buggy or hostile
     * teardown can point at {@code "recursive-backtracker"}, which would undo the collision
     * guard from the other direction: a plugin that cannot replace a built-in could otherwise
     * simply delete it.
     *
     * @param id the solver id to remove
     * @return {@code true} if something was removed
     * @throws IllegalArgumentException if {@code id} names a built-in
     */
    public boolean unregister(String id) {
        if (builtInIds.contains(id)) {
            throw new IllegalArgumentException(
                    "'" + id + "' is a built-in solver and cannot be unregistered. Only "
                            + "plugin-contributed algorithms can be removed.");
        }
        return solvers.remove(id) != null;
    }

    /** Every registered id, for callers that need to diff the registry across an operation. */
    public Set<String> ids() {
        return Set.copyOf(solvers.keySet());
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
