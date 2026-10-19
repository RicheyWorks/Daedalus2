// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/** The real fish tables from the repository, plus a tiny hand-made one. */
final class FishTestData {

    private FishTestData() {
    }

    static String read(String name) {
        Path p = Path.of("..", "data", "rpg", name);
        try {
            return Files.readString(p, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    static FishTable prism() {
        return FishTable.fromJson(read("prism-fish.json"));
    }

    static FishTable sky() {
        return FishTable.fromJson(read("skyisland-fish.json"));
    }

    /** Weights 3 : 1, rare one feeds at night with weight 3. */
    static FishTable pair() {
        return new FishTable("test", List.of(
                FishSpecies.of("minnow", Rarity.COMMON, 3, 1.0, 5),
                new FishSpecies("moonfish", Rarity.RARE, 1, 3, 0.5, "", 100, "", List.of(), List.of(), false)));
    }
}
