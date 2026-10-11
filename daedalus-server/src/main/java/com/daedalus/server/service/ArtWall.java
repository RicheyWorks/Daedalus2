// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.world.gallery.GalleryOps;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * The art people hang in a Gallery City (ADR-035), saved beside the world as {@code <world>.daew.art}:
 * one line per frame, {@code id x y z FACING w h seed owner title…}. A frame stores only its seed; the
 * picture is {@link com.daedalus.world.art.MazeArt} of that seed. Not thread-safe: the world service
 * calls it under its lock.
 */
final class ArtWall {

    /** A hung frame: where it is, what it shows, who hung it, and its title. */
    record Hung(String id, GalleryOps.Frame frame, String owner, String title) {
    }

    static final int MAX_TITLE = 60;

    private final Path file;
    private final TreeMap<String, Hung> frames = new TreeMap<>();
    private long next = 1;

    ArtWall(Path file) {
        this.file = file;
        load();
    }

    List<Hung> all() {
        return List.copyOf(frames.values());
    }

    Hung get(String id) {
        return frames.get(id);
    }

    Hung add(GalleryOps.Frame frame, String owner, String title) {
        String id = "art-" + next++;
        Hung h = new Hung(id, frame, owner, clean(title));
        frames.put(id, h);
        persist();
        return h;
    }

    void remove(String id) {
        if (frames.remove(id) != null) {
            persist();
        }
    }

    /** One line, printable, at most {@link #MAX_TITLE} characters; "Untitled" when empty. */
    static String clean(String title) {
        String t = title == null ? "" : title.replaceAll("\\p{Cntrl}", " ").strip();
        if (t.length() > MAX_TITLE) {
            t = t.substring(0, MAX_TITLE).strip();
        }
        return t.isEmpty() ? "Untitled" : t;
    }

    private void load() {
        if (!Files.exists(file)) {
            return;
        }
        try {
            for (String line : Files.readAllLines(file, StandardCharsets.UTF_8)) {
                String t = line.strip();
                if (t.isEmpty() || t.startsWith("#")) {
                    continue;
                }
                String[] p = t.split(" ", 10);
                if (p.length < 9 || !p[0].startsWith("art-")) {
                    throw new IOException("Bad art row: " + t);
                }
                GalleryOps.Frame f = new GalleryOps.Frame(Integer.parseInt(p[1]), Integer.parseInt(p[2]),
                        Integer.parseInt(p[3]), GalleryOps.Facing.valueOf(p[4]), Integer.parseInt(p[5]),
                        Integer.parseInt(p[6]), Long.parseLong(p[7]));
                frames.put(p[0], new Hung(p[0], f, p[8], p.length > 9 ? p[9] : "Untitled"));
                next = Math.max(next, Long.parseLong(p[0].substring(4)) + 1);
            }
        } catch (IOException | IllegalArgumentException e) {
            throw new IllegalStateException("Cannot read the art " + file, e);
        }
    }

    private void persist() {
        List<String> rows = new ArrayList<>();
        rows.add("# Daedalus gallery art (ADR-035): id x y z facing w h seed owner title");
        for (Map.Entry<String, Hung> e : frames.entrySet()) {
            GalleryOps.Frame f = e.getValue().frame();
            rows.add(e.getKey() + " " + f.x() + " " + f.y() + " " + f.z() + " " + f.facing().name() + " " + f.w() + " "
                    + f.h() + " " + f.seed() + " " + e.getValue().owner() + " " + e.getValue().title());
        }
        try {
            Path tmp = file.resolveSibling(file.getFileName() + ".tmp");
            Files.write(tmp, rows, StandardCharsets.UTF_8);
            Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException e) {
            throw new UncheckedIOException("Cannot persist the art " + file, e);
        }
    }
}
