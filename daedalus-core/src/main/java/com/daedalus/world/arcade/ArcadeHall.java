// SPDX-License-Identifier: MIT

package com.daedalus.world.arcade;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.Portal;
import com.daedalus.world.PortalResult;
import com.daedalus.world.PortalState;
import com.daedalus.world.WorldId;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

/**
 * Prismheart Arcade Hall: a walk-in arcade hall that stands on an island and is entered through its doorway.
 *
 * <p>The art side (blender-team, {@code tools/blender/arcade_hall_kit.py} and {@code arcade_hall_assembler.py}) builds the hall
 * from 2 m modular pieces and writes {@value #RESOURCE}: one row per sample layout (size in 2 m cells, doorway cell on the
 * south edge, inside spawn point). The doorway piece carries {@code SOCKET_Door}; this class turns that into a {@link Portal}
 * placed on an island block, so the player walks from the island through the door and spawns just inside the hall.
 *
 * <p>Frame: hall metres map 1:1 to blocks (Y up). The doorway threshold sits on the island anchor block; the hall extends
 * along +X (width) and +Z (depth) from its south-west corner, so the inside spawn is {@code anchor + (0, 0, insideZ)}.
 * Entering for the first time completes quest {@link #QUEST_ID}. Status: NOT READY art, hook only.
 */
public final class ArcadeHall {

    /** Layout table written by the assembler. */
    public static final String RESOURCE = "arcade_hall_layouts.tsv";
    /** Quest completed when a player first walks into any arcade hall. */
    public static final String QUEST_ID = "q_arcade_hall_enter";
    /** In-world name. */
    public static final String HALL_NAME = "The Prismheart Arcade Hall";
    /** Grid size of the modular kit, metres (= blocks). */
    public static final int GRID = 2;
    /** Wall height of the kit, metres. */
    public static final int HEIGHT = 4;
    /** The hall floor sits on Foundation_2m plinths this far above island grade (metres); EntranceSteps climb it in 3 steps. */
    public static final double FOUNDATION_M = 0.4;
    /** Horizontal run of the EntranceSteps out from the doorway, metres. */
    public static final double STEPS_RUN_M = 0.9;
    /** Number of 1.6 m PathTile slabs the assembler lays from the foot of the steps out onto the island. */
    public static final int PATH_TILES = 3;
    /** Path slab length, metres. */
    public static final double PATH_TILE_M = 1.6;

    /** One sample layout from the assembler. */
    public record Layout(String id, String title, int cellsW, int cellsD, int doorCell, double spawnInsideX, double spawnInsideY,
            int props, int cabs) {

        public Layout {
            Objects.requireNonNull(id, "id");
            if (cellsW < 2 || cellsD < 2) {
                throw new IllegalArgumentException("hall must be at least 2 x 2 cells: " + id);
            }
            if (doorCell < 0 || doorCell >= cellsW) {
                throw new IllegalArgumentException("doorway cell off the south edge: " + id);
            }
        }

        public int widthM() {
            return cellsW * GRID;
        }

        public int depthM() {
            return cellsD * GRID;
        }

        /** Doorway centre along the south wall, metres from the south-west corner. */
        public double doorX() {
            return doorCell * GRID + GRID / 2.0;
        }
    }

    /** Result of walking through the door. */
    public record Entry(boolean entered, boolean firstVisit, BlockCoordinate spawn, PortalResult portal) {
    }

    private final Layout layout;
    private final Portal door;
    private final BlockCoordinate anchor;
    private boolean visited;

    private ArcadeHall(Layout layout, WorldId world, BlockCoordinate anchor) {
        this.layout = layout;
        this.anchor = anchor;
        this.door = new Portal("arcade-hall-" + layout.id(), world, anchor, PortalState.SEALED);
    }

    /** Places a hall of {@code layoutId} on an island; {@code doorAnchor} is the island block under the doorway threshold. */
    public static ArcadeHall onIsland(String layoutId, WorldId world, BlockCoordinate doorAnchor) {
        Objects.requireNonNull(world, "world");
        Objects.requireNonNull(doorAnchor, "doorAnchor");
        Layout l = layout(layoutId).orElseThrow(() -> new IllegalArgumentException("unknown arcade hall layout: " + layoutId));
        return new ArcadeHall(l, world, doorAnchor);
    }

    public Layout layout() {
        return layout;
    }

    public Portal door() {
        return door;
    }

    /** South-west floor corner of the hall in blocks. */
    public BlockCoordinate corner() {
        return new BlockCoordinate(anchor.x() - (int) Math.floor(layout.doorX()), anchor.y(), anchor.z());
    }

    /** True if the block is on the hall floor (inside the walls). */
    public boolean inside(BlockCoordinate b) {
        BlockCoordinate c = corner();
        return b.y() == anchor.y() && b.x() >= c.x() && b.x() < c.x() + layout.widthM() && b.z() > c.z() && b.z() < c.z() + layout.depthM();
    }

    /** Island block at the foot of the entrance steps, straight out from the doorway (-Z); the island grade there is
     * {@link #FOUNDATION_M} below the hall floor, which is under one block, so it shares the anchor's Y. */
    public BlockCoordinate stepsFoot() {
        return new BlockCoordinate(anchor.x(), anchor.y(), anchor.z() - (int) Math.ceil(STEPS_RUN_M));
    }

    /** Island block where the glowing path to the door begins (the far end of the path slabs). */
    public BlockCoordinate pathStart() {
        return new BlockCoordinate(anchor.x(), anchor.y(), anchor.z() - (int) Math.ceil(STEPS_RUN_M + PATH_TILES * PATH_TILE_M));
    }

    /** Opens the doorway (the hall is open for business). */
    public PortalResult open() {
        return door.open();
    }

    /** Walk in from the island: opens the door if needed, returns the inside spawn block. */
    public Entry enter() {
        PortalResult r = door.state() == PortalState.OPEN ? PortalResult.ALREADY_OPEN : door.open();
        BlockCoordinate spawn = new BlockCoordinate(
                anchor.x() + (int) Math.round(layout.spawnInsideX() - layout.doorX()), anchor.y(), anchor.z() + (int) Math.ceil(layout.spawnInsideY()));
        boolean first = !visited;
        visited = true;
        return new Entry(true, first, spawn, r);
    }

    /** One-line in-world description. */
    public String describe() {
        return HALL_NAME + " (" + layout.title() + "): " + layout.cabs() + " cabinets, " + layout.props() + " props";
    }

    // ---------------------------------------------------------------- layout table

    private static volatile List<Layout> cache;

    /** All sample layouts, in assembler order. */
    public static List<Layout> layouts() {
        List<Layout> c = cache;
        if (c == null) {
            c = load();
            cache = c;
        }
        return c;
    }

    public static Optional<Layout> layout(String id) {
        return layouts().stream().filter(l -> l.id().equals(id)).findFirst();
    }

    private static List<Layout> load() {
        try (InputStream in = ArcadeHall.class.getResourceAsStream(RESOURCE)) {
            if (in == null) {
                throw new IllegalStateException("Arcade hall layouts missing: " + RESOURCE);
            }
            return parse(new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8)));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    static List<Layout> parse(BufferedReader r) throws IOException {
        List<Layout> out = new ArrayList<>();
        for (String line = r.readLine(); line != null; line = r.readLine()) {
            if (line.isBlank() || line.startsWith("#")) {
                continue;
            }
            String[] f = line.split("\t");
            if (f.length != 9) {
                throw new IllegalArgumentException("bad arcade hall row: " + line);
            }
            out.add(new Layout(f[0], f[1], Integer.parseInt(f[2]), Integer.parseInt(f[3]), Integer.parseInt(f[4]),
                    Double.parseDouble(f[5]), Double.parseDouble(f[6]), Integer.parseInt(f[7]), Integer.parseInt(f[8])));
        }
        return Collections.unmodifiableList(out);
    }
}
