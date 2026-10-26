// SPDX-License-Identifier: MIT
package com.daedalus.explore;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

/**
 * The community controller database (SDL_GameControllerDB, zlib; vendored in data/controllers and copied here by
 * tools/controllers/build_bundle.py). GLFW reads this format directly, so every pad it lists, from Xbox and
 * Razer pads to N64/Saturn adapters, Sega and Atari pads and arcade sticks, works as a standard gamepad here.
 * The web clients read the same database through controller-bundle.json.
 */
public final class PadMappings {
    public static final String RESOURCE = "/controllers/gamecontrollerdb.txt";

    private PadMappings() {
    }

    /** The database text, or an empty string if the resource is missing. */
    public static String load() {
        try (InputStream in = PadMappings.class.getResourceAsStream(RESOURCE)) {
            return in == null ? "" : new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            return "";
        }
    }

    /** Mapping lines for one GLFW platform name ("Windows", "Mac OS X", "Linux"). */
    public static long count(String text, String platform) {
        return text.lines().filter(l -> !l.isBlank() && !l.startsWith("#") && l.contains("platform:" + platform + ",")).count();
    }

    /** GLFW's platform name for this JVM. */
    public static String platform() {
        String os = System.getProperty("os.name", "").toLowerCase(java.util.Locale.ROOT);
        return os.contains("win") ? "Windows" : os.contains("mac") ? "Mac OS X" : "Linux";
    }
}
