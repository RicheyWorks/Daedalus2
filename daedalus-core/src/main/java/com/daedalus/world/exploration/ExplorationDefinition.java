// SPDX-License-Identifier: MIT
package com.daedalus.world.exploration;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Immutable original exploration design data. It does not allocate a session realm or a land deed. */
public record ExplorationDefinition(String id, int version, String title, String hub,
                                    List<World> worlds, List<Portal> portals, List<Collectible> collectibles,
                                    List<Objective> objectives, List<Module> modules) {
    public static final int MAX_WORLDS = 16;
    public static final int MAX_PORTALS = 64;
    public static final int MAX_OBJECTIVES = 128;
    public static final int MAX_COLLECTIBLES = 256;

    public enum Kind { VISIT, REACH, COLLECT }

    /** Metres, XYZ with Y up, matching the existing world wire. */
    public record Point(double x, double y, double z) {
        public Point {
            finite(x, -2048, 2048);
            finite(y, -2048, 2048);
            finite(z, -2048, 2048);
        }
    }

    /** Presentation and movement intent; the existing native controller remains the execution owner. */
    public record Movement(double walkMetresPerSecond, double jumpMetres, boolean ledgeClimb,
                           boolean shortGlide, String hint) {
        public Movement {
            finite(walkMetresPerSecond, 1, 12);
            finite(jumpMetres, 0, 8);
            text(hint, 160);
        }
    }

    public record Marker(String id, Point position, boolean secret, String hint) {
        public Marker { token(id); require(position != null, "marker position"); text(hint, 160); }
    }

    public record Placement(String id, String module, Point position, double yawDegrees) {
        public Placement {
            token(id); token(module); require(position != null, "placement position");
            finite(yawDegrees, -360, 360);
        }
    }

    public record Module(String id, String role, double width, double height, double depth, List<String> sockets) {
        public Module {
            token(id); text(role, 80);
            finite(width, 0.25, 64); finite(height, 0.25, 64); finite(depth, 0.25, 64);
            sockets = copy(sockets, 16); unique(sockets);
        }
    }

    public record World(String id, String title, String theme, Point spawn, Movement movement,
                        List<Marker> markers, List<Placement> placements) {
        public World {
            token(id); text(title, 80); text(theme, 160);
            require(spawn != null && movement != null, "world spawn and movement");
            markers = copy(markers, 64); placements = copy(placements, 128);
            unique(markers.stream().map(Marker::id).toList());
            unique(placements.stream().map(Placement::id).toList());
        }
    }

    /** A portal marker is part of its source world; landingMarker belongs to its destination. */
    public record Portal(String id, String from, String to, String marker, String landingMarker,
                         String visual, int collectedRequired, List<String> objectivesRequired) {
        public Portal {
            token(id); token(from); token(to); token(marker); token(landingMarker); text(visual, 160);
            require(!from.equals(to), "portal must cross worlds");
            require(collectedRequired >= 0 && collectedRequired <= MAX_COLLECTIBLES, "portal collection count");
            objectivesRequired = copy(objectivesRequired, MAX_OBJECTIVES); unique(objectivesRequired);
        }
        public boolean free() { return collectedRequired == 0 && objectivesRequired.isEmpty(); }
    }

    public record Collectible(String id, String world, Point position, boolean secret, String hint) {
        public Collectible { token(id); token(world); require(position != null, "collectible position"); text(hint, 160); }
    }

    /** Targets are marker IDs for REACH and collectible IDs for COLLECT. VISIT has no targets. */
    public record Objective(String id, String world, String title, Kind kind, List<String> targets,
                            List<String> prerequisites) {
        public Objective {
            token(id); token(world); text(title, 100); require(kind != null, "objective kind");
            targets = copy(targets, MAX_COLLECTIBLES); unique(targets);
            prerequisites = copy(prerequisites, MAX_OBJECTIVES); unique(prerequisites);
            require(kind == Kind.VISIT ? targets.isEmpty() : !targets.isEmpty(), "objective targets");
        }
    }

    public ExplorationDefinition {
        token(id); text(title, 80); token(hub); require(version > 0, "definition version");
        worlds = copy(worlds, MAX_WORLDS); portals = copy(portals, MAX_PORTALS);
        collectibles = copy(collectibles, MAX_COLLECTIBLES); objectives = copy(objectives, MAX_OBJECTIVES);
        modules = copy(modules, 128); require(!worlds.isEmpty(), "worlds required");
        unique(worlds.stream().map(World::id).toList()); unique(portals.stream().map(Portal::id).toList());
        unique(collectibles.stream().map(Collectible::id).toList()); unique(objectives.stream().map(Objective::id).toList());
        unique(modules.stream().map(Module::id).toList());
        Set<String> worldIds = new HashSet<>(worlds.stream().map(World::id).toList());
        Set<String> objectiveIds = new HashSet<>(objectives.stream().map(Objective::id).toList());
        Set<String> moduleIds = new HashSet<>(modules.stream().map(Module::id).toList());
        require(worldIds.contains(hub), "unknown hub");
        Set<String> markerIds = new HashSet<>();
        for (World w : worlds) {
            for (Marker m : w.markers()) require(markerIds.add(m.id()), "marker IDs must be globally unique");
            for (Placement p : w.placements()) require(moduleIds.contains(p.module()), "unknown module");
        }
        for (Collectible c : collectibles) require(worldIds.contains(c.world()), "unknown collectible world");
        for (Objective o : objectives) {
            require(worldIds.contains(o.world()), "unknown objective world");
            require(objectiveIds.containsAll(o.prerequisites()), "unknown prerequisite");
            for (String target : o.targets()) {
                boolean found = o.kind() == Kind.REACH
                        ? hasMarker(worlds, o.world(), target)
                        : collectibles.stream().anyMatch(c -> c.id().equals(target) && c.world().equals(o.world()));
                require(found, "objective target must belong to its world");
            }
        }
        Set<String> sorted = new HashSet<>();
        for (int pass = 0; pass < objectives.size(); pass++) {
            for (Objective o : objectives) if (sorted.containsAll(o.prerequisites())) sorted.add(o.id());
        }
        require(sorted.size() == objectives.size(), "cyclic prerequisites");
        for (Portal p : portals) {
            require(worldIds.contains(p.from()) && worldIds.contains(p.to()), "unknown portal world");
            require(hasMarker(worlds, p.from(), p.marker()), "unknown source marker");
            require(hasMarker(worlds, p.to(), p.landingMarker()), "unknown landing marker");
            require(objectiveIds.containsAll(p.objectivesRequired()), "unknown portal prerequisite");
            require(p.collectedRequired() <= collectibles.size(), "unreachable collection count");
        }
        // Every world must have a return route which requires no collectible or objective unlock.
        Set<String> returns = new HashSet<>(); returns.add(hub);
        Set<String> reachable = new HashSet<>(); reachable.add(hub);
        for (int pass = 0; pass < worlds.size(); pass++) {
            for (Portal p : portals) {
                if (p.free() && returns.contains(p.to())) returns.add(p.from());
                if (reachable.contains(p.from())) reachable.add(p.to());
            }
        }
        require(returns.containsAll(worldIds) && reachable.containsAll(worldIds), "worlds need hub and free return routes");
    }

    public World world(String worldId) { return worlds.stream().filter(w -> w.id().equals(worldId)).findFirst().orElse(null); }
    public Portal portal(String portalId) { return portals.stream().filter(p -> p.id().equals(portalId)).findFirst().orElse(null); }
    public Collectible collectible(String collectibleId) {
        return collectibles.stream().filter(c -> c.id().equals(collectibleId)).findFirst().orElse(null);
    }
    public boolean markerIn(String worldId, String markerId) { return hasMarker(worlds, worldId, markerId); }

    /** Shortest unconditional route home; progression reserves enough replay slots to finish it. */
    public int freeReturnHops(String worldId) {
        if (world(worldId) == null) return -1;
        Set<String> reached = new HashSet<>(); reached.add(worldId);
        for (int hops = 0; hops < worlds.size(); hops++) {
            if (reached.contains(hub)) return hops;
            Set<String> next = new HashSet<>(reached);
            for (Portal portal : portals) {
                if (portal.free() && reached.contains(portal.from())) next.add(portal.to());
            }
            reached = next;
        }
        return -1;
    }

    private static boolean hasMarker(List<World> worlds, String worldId, String markerId) {
        return worlds.stream().anyMatch(w -> w.id().equals(worldId) && w.markers().stream().anyMatch(m -> m.id().equals(markerId)));
    }
    static void token(String value) {
        require(value != null && value.matches("[a-z][a-z0-9-]{0,47}"), "invalid design identifier");
    }
    static void text(String value, int limit) {
        require(value != null && !value.isBlank() && value.length() <= limit, "invalid design text");
    }
    static void finite(double value, double min, double max) {
        require(Double.isFinite(value) && value >= min && value <= max, "invalid finite range");
    }
    static void require(boolean condition, String reason) {
        if (!condition) throw new IllegalArgumentException(reason);
    }
    private static <T> List<T> copy(List<T> values, int max) {
        require(values != null && values.size() <= max, "definition capacity");
        return List.copyOf(values);
    }
    private static void unique(List<String> values) {
        values.forEach(ExplorationDefinition::token);
        require(new HashSet<>(values).size() == values.size(), "duplicate design identifier");
    }
}
