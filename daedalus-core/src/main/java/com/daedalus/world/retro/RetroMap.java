// SPDX-License-Identifier: MIT

package com.daedalus.world.retro;

import java.util.Arrays;

/**
 * One map of the realm (ADR-052): the field, a town, the castle, a cave floor. A grid of {@link RetroTile}s, plus,
 * where monsters roam, one encounter-zone character per tile ({@code '.'} for none; the zone tables are in the realm).
 *
 * <p>Mutable while the generator builds it; the realm hands out the finished maps and nobody changes them after.
 */
public final class RetroMap {

    private final String id;
    private final String title;
    private final int width;
    private final int height;
    private final String music;
    private final boolean dark;
    private final RetroRealm.Place exit;
    private final RetroTile[] tiles;
    private final char[] zones;

    /**
     * @param id     short id used in the spec (FIELD, TOWN1, CASTLE, CAVE1...)
     * @param title  the name on screen
     * @param music  the jukebox cue played here (FIELD, TOWN, CASTLE, CAVE)
     * @param dark   a cave: the party sees only as far as its torch
     * @param exit   where walking off the edge leads, or null (the field has no edge to walk off)
     * @param fill   the tile everything starts as
     */
    public RetroMap(String id, String title, int width, int height, String music, boolean dark, RetroRealm.Place exit,
                    RetroTile fill) {
        if (width < 1 || height < 1) {
            throw new IllegalArgumentException("a map needs at least one tile");
        }
        this.id = id;
        this.title = title;
        this.width = width;
        this.height = height;
        this.music = music;
        this.dark = dark;
        this.exit = exit;
        this.tiles = new RetroTile[width * height];
        Arrays.fill(tiles, fill);
        this.zones = new char[width * height];
        Arrays.fill(zones, '.');
    }

    public String id() {
        return id;
    }

    public String title() {
        return title;
    }

    public int width() {
        return width;
    }

    public int height() {
        return height;
    }

    public String music() {
        return music;
    }

    public boolean dark() {
        return dark;
    }

    public RetroRealm.Place exit() {
        return exit;
    }

    public boolean inside(int x, int y) {
        return x >= 0 && y >= 0 && x < width && y < height;
    }

    /** The tile at (x, y); outside the map, what the screen shows there: rock in a cave, sea round the field, grass
     *  round a town. */
    public RetroTile at(int x, int y) {
        if (!inside(x, y)) {
            return outside();
        }
        return tiles[y * width + x];
    }

    public RetroTile outside() {
        return dark ? RetroTile.WALL : exit == null ? RetroTile.WATER : RetroTile.GRASS;
    }

    public void set(int x, int y, RetroTile t) {
        if (inside(x, y)) {
            tiles[y * width + x] = t;
        }
    }

    /** The encounter zone at (x, y), or '.' where nothing attacks. */
    public char zoneAt(int x, int y) {
        return inside(x, y) ? zones[y * width + x] : '.';
    }

    public void setZone(int x, int y, char zone) {
        if (inside(x, y)) {
            zones[y * width + x] = zone;
        }
    }

    /** True when any tile has an encounter zone. */
    public boolean hasEncounters() {
        for (char z : zones) {
            if (z != '.') {
                return true;
            }
        }
        return false;
    }

    /** One row as spec characters. */
    public String row(int y) {
        StringBuilder sb = new StringBuilder(width);
        for (int x = 0; x < width; x++) {
            sb.append(at(x, y).code());
        }
        return sb.toString();
    }

    /** One row of zone characters. */
    public String zoneRow(int y) {
        return new String(zones, y * width, width);
    }

    /** How many tiles are {@code t}. */
    public int count(RetroTile t) {
        int n = 0;
        for (RetroTile x : tiles) {
            if (x == t) {
                n++;
            }
        }
        return n;
    }
}
