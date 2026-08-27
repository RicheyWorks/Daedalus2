// SPDX-License-Identifier: MIT

package com.daedalus.explore;

/**
 * Core-only entry. Without {@code DAEDALUS_EXPLORE=1} or {@code --window}
 * this prints the story JSON and never loads GLFW natives.
 */
public final class ExploreLauncher {

    public static final String WINDOW_ENV = "DAEDALUS_EXPLORE";
    public static final String WINDOW_FLAG = "--window";

    private ExploreLauncher() {
    }

    public static void main(String[] args) {
        ExploreWorld world = ExploreWorld.dungeon();
        if (windowRequested(args)) {
            runWindow(world);
            return;
        }
        System.out.println(ExploreStory.export(world));
    }

    public static boolean windowRequested(String[] args) {
        if ("1".equals(System.getenv(WINDOW_ENV))) {
            return true;
        }
        if (args == null) {
            return false;
        }
        for (String arg : args) {
            if (WINDOW_FLAG.equals(arg)) {
                return true;
            }
        }
        return false;
    }

    static void runWindow(ExploreWorld world) {
        try {
            Class<?> host = Class.forName("com.daedalus.explore.glfw.ExploreHost");
            host.getMethod("run", ExploreWorld.class).invoke(null, world);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException(
                    "GLFW host failed to start — check LWJGL natives and a display", e);
        }
    }
}
