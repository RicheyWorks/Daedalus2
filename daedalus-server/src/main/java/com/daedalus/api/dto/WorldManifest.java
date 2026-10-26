// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import com.fasterxml.jackson.annotation.JsonInclude;

import java.util.List;

/**
 * The manifest of a Daedalus World Package (ADR-032): everything an engine needs to stand a world up
 * besides its geometry. Geometry is {@code world.glb} (glTF 2.0, one node per 16³ chunk); assets made in
 * Blender ship beside it. Coordinates are glTF's: metres, +Y up, right-handed — the same numbers the
 * live API uses, so an engine can load the package and then follow {@code /topic/world/{id}/…} frames.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record WorldManifest(String format, int version, String generator, World world, String units, String axes,
                            Geometry geometry, List<Swatch> palette, List<Island> islands, List<Plot> plots,
                            Obby obby, List<Art> art, List<Gate> gates, List<Ark> arks, Mount mount, List<Asset> assets,
                            Live live, Chain chain) {

    /** Copy on construct: the caller's lists cannot change what this manifest says. */
    public WorldManifest {
        palette = palette == null ? List.of() : List.copyOf(palette);
        islands = islands == null ? List.of() : List.copyOf(islands);
        plots = plots == null ? List.of() : List.copyOf(plots);
        art = art == null ? List.of() : List.copyOf(art);
        gates = gates == null ? List.of() : List.copyOf(gates);
        arks = arks == null ? List.of() : List.copyOf(arks);
        assets = assets == null ? List.of() : List.copyOf(assets);
    }

    /** Which world, as of which revision. */
    public record World(String id, String style, String title, long seed, long revision) {
    }

    /** The geometry file and what is in it. */
    public record Geometry(String file, int chunkSize, int chunks, long triangles, List<String> materials) {

        public Geometry {
            materials = materials == null ? List.of() : List.copyOf(materials);
        }
    }

    /**
     * A cube type's ordinal (the byte in {@code /chunk/blocks}), colour (sRGB hex), whether it blends, and
     * whether the faces of its neighbours show through it (clouds do without blending).
     */
    public record Swatch(int ordinal, String type, String rgb, boolean translucent, boolean seeThrough) {
    }

    /** A raised island: where it sits and where its dock is, as [x, y, z]. */
    public record Island(int slot, long seed, int radius, List<Integer> origin, List<Integer> dock, String owner) {

        public Island {
            origin = List.copyOf(origin);
            dock = List.copyOf(dock);
        }
    }

    /** A Parcels world's plot (ADR-033): its footprint corners as [x, y, z], what it opened with, its owner. */
    public record Plot(int n, List<Integer> min, List<Integer> max, String show, String owner) {

        public Plot {
            min = List.copyOf(min);
            max = List.copyOf(max);
        }
    }

    /**
     * A Bricks world's obby (ADR-034): where avatars spawn, the lava's top, and the platforms in order (the
     * finish last), each as its footprint corners [x, y, z] with whether it is a checkpoint.
     */
    public record Obby(List<Integer> spawn, int lavaY, List<Step> steps) {

        public Obby {
            spawn = List.copyOf(spawn);
            steps = List.copyOf(steps);
        }
    }

    /**
     * A frame in a Gallery City (ADR-035): the wall cube at its lowest corner as [x, y, z], the side it
     * hangs on, its size, and the seed of the maze art it shows (served at {@code image}).
     */
    public record Art(String id, List<Integer> at, String facing, int w, int h, long seed, String title, String image) {

        public Art {
            at = List.copyOf(at);
        }
    }

    /** One platform of an obby. */
    public record Step(int n, List<Integer> min, List<Integer> max, boolean checkpoint, boolean finish) {

        public Step {
            min = List.copyOf(min);
            max = List.copyOf(max);
        }
    }

    /** A sky gate (ADR-031): its doorway, the cloud berth an ark ties up at, and where it leads. */
    public record Gate(int gate, int slot, List<Integer> center, List<Integer> berth, String toWorld, String toTitle,
                       int toGate) {

        public Gate {
            center = List.copyOf(center);
            berth = List.copyOf(berth);
        }
    }

    /** An ark (ADR-022): home island, where it is or is bound, and its berth there. */
    public record Ark(String id, String name, int homeSlot, int slot, List<Integer> berth, String state) {

        public Ark {
            berth = List.copyOf(berth);
        }
    }

    /** What flies to this world's gates (ADR-031). */
    public record Mount(String kind, boolean ready) {
    }

    /** A model that ships with the package, and how to place it. */
    public record Asset(String name, String file, String use) {
    }

    /** Where the live world is, for an engine that wants to follow it after loading. */
    public record Live(String api, String frames) {
    }

    /** The deed contract, when one is configured (ADR-028). */
    public record Chain(long chainId, String deedContract, String tokenBase) {
    }
}
