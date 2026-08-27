// SPDX-License-Identifier: MIT

package com.daedalus.explore;

/**
 * Core-only entry. Without {@code DAEDALUS_EXPLORE=1} or {@code --window}
 * this prints the story JSON and never loads GLFW natives.
 */
public final class ExploreLauncher {

    public static final String WINDOW_ENV = "DAEDALUS_EXPLORE";
    public static final String WINDOW_FLAG = "--window";
    public static final String SMOKE_FLAG = "--smoke";

    private ExploreLauncher() {
    }

    public static void main(String[] args) {
        ExploreWorld world = ExploreWorld.dungeon();
        boolean smoke = flag(args, SMOKE_FLAG);
        if (windowRequested(args) || smoke) {
            runWindow(world, smoke);
            if (smoke) {
                System.out.println("DAEDALUS_EXPLORE_SMOKE_OK");
            }
            return;
        }
        System.out.println(ExploreStory.export(world));
    }

    public static boolean windowRequested(String[] args) {
        if ("1".equals(System.getenv(WINDOW_ENV))) {
            return true;
        }
        return flag(args, WINDOW_FLAG);
    }

    public static boolean flag(String[] args, String name) {
        if (args == null || name == null) {
            return false;
        }
        for (String arg : args) {
            if (name.equals(arg)) {
                return true;
            }
        }
        return false;
    }

    static void runWindow(ExploreWorld world) {
        runWindow(world, false);
    }

    static void runWindow(ExploreWorld world, boolean smoke) {
        try {
            Class<?> host = Class.forName("com.daedalus.explore.glfw.ExploreHost");
            host.getMethod("run", ExploreWorld.class, boolean.class)
                    .invoke(null, world, smoke);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException(
                    "GLFW host failed to start — check LWJGL natives and a display", e);
        }
    }
}
