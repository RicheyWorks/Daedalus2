// SPDX-License-Identifier: MIT

package com.daedalus.mazegame;

import java.io.IOException;
import java.io.Reader;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Optional;
import java.util.Properties;

/**
 * Local-only best scores, one line per share code, in a properties file under the player's home
 * directory ({@code ~/.labyrinth-run/best-scores.properties}). No network, nothing secret, never
 * committed. Value format: {@code score,stars,moves,millis}.
 */
public final class BestScores {

    private final Path file;
    private final Properties props = new Properties();

    public BestScores(Path file) throws IOException {
        this.file = file;
        if (Files.exists(file)) {
            try (Reader r = Files.newBufferedReader(file, StandardCharsets.UTF_8)) {
                props.load(r);
            }
        }
    }

    public static Path defaultFile() {
        return Path.of(System.getProperty("user.home"), ".labyrinth-run", "best-scores.properties");
    }

    public Path file() { return file; }

    /** Best score so far for a share code, if any. */
    public Optional<Integer> best(String code) {
        String v = props.getProperty(code);
        if (v == null) {
            return Optional.empty();
        }
        try {
            return Optional.of(Integer.parseInt(v.split(",", 2)[0].trim()));
        } catch (NumberFormatException e) {
            return Optional.empty();
        }
    }

    /** Stores the result when it beats the previous best; returns whether it did. */
    public boolean record(String code, int score, int stars, int moves, long millis) throws IOException {
        Optional<Integer> prev = best(code);
        if (prev.isPresent() && prev.get() >= score) {
            return false;
        }
        props.setProperty(code, score + "," + stars + "," + moves + "," + millis);
        Path dir = file.toAbsolutePath().getParent();
        if (dir != null) {
            Files.createDirectories(dir);
        }
        try (Writer w = Files.newBufferedWriter(file, StandardCharsets.UTF_8)) {
            props.store(w, "Labyrinth Run local best scores (score,stars,moves,millis)");
        }
        return true;
    }
}
