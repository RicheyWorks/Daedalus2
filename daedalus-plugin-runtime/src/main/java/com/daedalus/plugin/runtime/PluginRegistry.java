// SPDX-License-Identifier: MIT

package com.daedalus.plugin.runtime;

import com.daedalus.plugin.MazePlugin;
import com.daedalus.plugin.PluginLifecycle;
import com.daedalus.plugin.PluginManifest;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Tracks loaded plugins by id and their lifecycle state.
 */
public class PluginRegistry {

    public record Entry(MazePlugin plugin, PluginManifest manifest, PluginLifecycle state, Throwable error) {
        public Entry advance(PluginLifecycle next) { return new Entry(plugin, manifest, next, error); }
        public Entry fail(Throwable t)             { return new Entry(plugin, manifest, PluginLifecycle.FAILED, t); }
    }

    private final Map<String, Entry> entries = new ConcurrentHashMap<>();

    public void put(MazePlugin plugin) {
        PluginManifest m = plugin.manifest();
        Entry claimed = new Entry(plugin, m, PluginLifecycle.DISCOVERED, null);
        Entry incumbent = entries.putIfAbsent(m.id(), claimed);
        if (incumbent != null) {
            throw new IllegalArgumentException(
                    "plugin id '" + m.id() + "' is already claimed by "
                            + incumbent.plugin().getClass().getName()
                            + "; a later JAR cannot silently replace it");
        }
    }

    public Entry get(String id) { return entries.get(id); }

    public Collection<Entry> all() {
        return Collections.unmodifiableCollection(entries.values());
    }

    public void advance(String id, PluginLifecycle next) {
        entries.computeIfPresent(id, (k, e) -> e.advance(next));
    }

    public void fail(String id, Throwable t) {
        entries.computeIfPresent(id, (k, e) -> e.fail(t));
    }

    public int size() { return entries.size(); }

    public List<Entry> sortedByDependencies() {
        // Topological sort: plugins listed in `requires` come first.
        List<Entry> all = new ArrayList<>(entries.values());
        List<Entry> result = new ArrayList<>(all.size());
        Set<String> emitted = new HashSet<>();
        boolean progressed = true;
        while (progressed && !all.isEmpty()) {
            progressed = false;
            Iterator<Entry> it = all.iterator();
            while (it.hasNext()) {
                Entry e = it.next();
                boolean deps = true;
                for (String req : e.manifest().requires()) {
                    if (!emitted.contains(req)) { deps = false; break; }
                }
                if (deps) {
                    result.add(e);
                    emitted.add(e.manifest().id());
                    it.remove();
                    progressed = true;
                }
            }
        }
        if (!all.isEmpty()) {
            List<String> stuck = new ArrayList<>();
            for (Entry e : all) {
                stuck.add(e.manifest().id());
            }
            throw new IllegalStateException(
                    "Unsatisfiable plugin dependencies (cycle or missing requires): " + stuck);
        }
        return result;
    }
}
