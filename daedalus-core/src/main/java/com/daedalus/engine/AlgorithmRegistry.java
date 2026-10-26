// SPDX-License-Identifier: MIT

package com.daedalus.engine;

import com.daedalus.model.AlgorithmDescriptor;

import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Function;

/**
 * Shared map for generators and solvers. The two public registries used to be
 * near-copies of register / unregister / require; a lifecycle bug had to be
 * fixed twice, and one side could drift. Both now delegate here.
 *
 * @param <T> {@code MazeGenerator} or {@code MazeSolver}
 */
public final class AlgorithmRegistry<T> {

    private final Map<String, T> entries = new ConcurrentHashMap<>();
    private final Set<String> builtInIds;
    private final String kind;
    private final Function<T, String> idOf;
    private final Function<T, AlgorithmDescriptor> descriptorOf;

    public AlgorithmRegistry(List<T> builtIn, String kind,
                             Function<T, String> idOf,
                             Function<T, AlgorithmDescriptor> descriptorOf) {
        this.kind = kind;
        this.idOf = idOf;
        this.descriptorOf = descriptorOf;
        builtIn.forEach(this::register);
        this.builtInIds = Set.copyOf(entries.keySet());
    }

    public void register(T algorithm) {
        String id = idOf.apply(algorithm);
        T incumbent = entries.putIfAbsent(id, algorithm);
        if (incumbent != null) {
            throw new DuplicateAlgorithmException(
                    kind, id, incumbent.getClass(), algorithm.getClass());
        }
    }

    /**
     * Removes a plugin-contributed algorithm. Built-ins are refused so a
     * teardown cannot delete {@code recursive-backtracker} and undo the
     * collision guard from the other direction.
     */
    public boolean unregister(String id) {
        if (builtInIds.contains(id)) {
            throw new IllegalArgumentException(
                    "'" + id + "' is a built-in " + kind + " and cannot be unregistered. Only "
                            + "plugin-contributed algorithms can be removed.");
        }
        return entries.remove(id) != null;
    }

    public Set<String> ids() {
        return Set.copyOf(entries.keySet());
    }

    public Optional<T> find(String id) {
        return Optional.ofNullable(entries.get(id));
    }

    public T require(String id) {
        return find(id).orElseThrow(() -> new UnknownAlgorithmException(
                kind, id, entries.keySet().stream().sorted().toList()));
    }

    public Collection<T> all() {
        return Collections.unmodifiableCollection(entries.values());
    }

    public List<AlgorithmDescriptor> descriptors() {
        return entries.values().stream().map(descriptorOf).toList();
    }

    public int size() {
        return entries.size();
    }
}
