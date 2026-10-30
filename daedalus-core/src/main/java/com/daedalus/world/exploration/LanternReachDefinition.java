// SPDX-License-Identifier: MIT
package com.daedalus.world.exploration;

import com.daedalus.world.exploration.ExplorationDefinition.Collectible;
import com.daedalus.world.exploration.ExplorationDefinition.Kind;
import com.daedalus.world.exploration.ExplorationDefinition.Marker;
import com.daedalus.world.exploration.ExplorationDefinition.Module;
import com.daedalus.world.exploration.ExplorationDefinition.Movement;
import com.daedalus.world.exploration.ExplorationDefinition.Objective;
import com.daedalus.world.exploration.ExplorationDefinition.Placement;
import com.daedalus.world.exploration.ExplorationDefinition.Point;
import com.daedalus.world.exploration.ExplorationDefinition.Portal;
import com.daedalus.world.exploration.ExplorationDefinition.World;
import java.util.List;

/**
 * Provisional original design, not registered Daedalus canon or built geometry.
 * A surviving lantern archive links compact fragments of the shattered planet. Names, tuning and layouts are proposals.
 */
public final class LanternReachDefinition {
    private LanternReachDefinition() { }

    public static ExplorationDefinition create() {
        Movement ground = new Movement(5, 1.6, true, false, "Walk, hop and climb broad ledges; a visible route returns home.");
        Movement air = new Movement(5, 1.6, true, true, "Reach a marked launch ledge, then make a short glide to the next terrace.");
        List<Module> kit = List.of(
                new Module("portal-frame", "Lantern arch and preview surface", 6, 8, 2, List.of("entry", "preview")),
                new Module("step-block", "Broad climbable stone terrace", 6, 2, 6, List.of("top", "edge")),
                new Module("ramp", "Readable non-jump ascent", 6, 4, 12, List.of("low", "high")),
                new Module("bridge", "Ravine crossing or works catwalk", 4, 1, 12, List.of("near", "far")),
                new Module("lantern-plinth", "Objective landmark and token holder", 2, 3, 2, List.of("token")),
                new Module("secret-screen", "Reed curtain, hatch or star shutter", 4, 4, 1, List.of("entry")));
        World atrium = new World("atrium", "Lantern Atrium", "Warm archive stone, three living portal previews",
                p(0, 0, 0), ground,
                List.of(marker("atrium-return", 0, 0, 0, false, "The central lantern is home."),
                        marker("atrium-ravine", -16, 0, 12, false, "Reeds move inside the arch."),
                        marker("atrium-works", 16, 0, 12, false, "Copper wheels await two tokens and the ravine summit."),
                        marker("atrium-observatory", 0, 4, -18, false, "Five tokens and the works relay light this arch."),
                        marker("atrium-overlook", 0, 8, -8, false, "Climb the broad steps to see all three previews.")),
                List.of(place("atrium-gate-r", "portal-frame", -16, 0, 12, 0),
                        place("atrium-gate-w", "portal-frame", 16, 0, 12, 0),
                        place("atrium-gate-o", "portal-frame", 0, 4, -18, 180),
                        place("atrium-ascent", "ramp", 0, 0, -6, 180),
                        place("atrium-step", "step-block", 0, 4, -10, 0),
                        place("atrium-lantern", "lantern-plinth", 0, 8, -8, 0)));
        World ravine = new World("ravine", "Reedbell Ravine", "Teal water, rust cliffs and wind-bent reeds",
                p(0, 0, 0), ground,
                List.of(marker("ravine-arrival", 0, 0, 0, false, "The home lantern remains beside the landing."),
                        marker("ravine-home", 0, 0, -4, false, "Return to the Atrium at any time."),
                        marker("ravine-summit", 20, 12, 24, false, "The bell above the bridge marks the summit."),
                        marker("ravine-curtain", -8, 2, 18, true, "A pale reed leans against the water curtain.")),
                List.of(place("ravine-gate", "portal-frame", 0, 0, -4, 180),
                        place("ravine-ramp", "ramp", 8, 0, 10, 0),
                        place("ravine-bridge", "bridge", 14, 4, 20, 90),
                        place("ravine-terrace", "step-block", 20, 8, 24, 0),
                        place("ravine-bell", "lantern-plinth", 20, 12, 24, 0),
                        place("ravine-secret", "secret-screen", -8, 2, 18, 0)));
        World works = new World("works", "Coppercloud Works", "Rounded copper machinery, cream stone and amber signals",
                p(0, 0, 0), ground,
                List.of(marker("works-arrival", 0, 0, 0, false, "A home lantern sits behind the landing."),
                        marker("works-home", 0, 0, -4, false, "Return without spending a token."),
                        marker("works-relay", 24, 10, 16, false, "Follow the copper catwalk to the relay lever."),
                        marker("works-hatch", -10, 0, 18, true, "A loose amber bolt points toward a service hatch.")),
                List.of(place("works-gate", "portal-frame", 0, 0, -4, 180),
                        place("works-ramp", "ramp", 6, 0, 10, 0),
                        place("works-catwalk", "bridge", 16, 4, 16, 90),
                        place("works-tower", "step-block", 24, 6, 16, 0),
                        place("works-switch", "lantern-plinth", 24, 10, 16, 0),
                        place("works-secret", "secret-screen", -10, 0, 18, 0)));
        World observatory = new World("observatory", "Moonseed Observatory", "Indigo terraces, pale brass and floating seed lights",
                p(0, 0, 0), air,
                List.of(marker("observatory-arrival", 0, 0, 0, false, "The home lantern stays visible below."),
                        marker("observatory-home", 0, 0, -4, false, "Follow the indigo ramp home."),
                        marker("observatory-zenith", 20, 18, 18, false, "Glide from the launch terrace to the moonseed dial."),
                        marker("observatory-shutter", -12, 8, 14, true, "An unlit star hides a narrow shutter.")),
                List.of(place("observatory-gate", "portal-frame", 0, 0, -4, 180),
                        place("observatory-ramp", "ramp", 8, 0, 10, 0),
                        place("observatory-launch", "step-block", 14, 8, 14, 0),
                        place("observatory-landing", "step-block", 20, 14, 18, 0),
                        place("observatory-dial", "lantern-plinth", 20, 18, 18, 0),
                        place("observatory-secret", "secret-screen", -12, 8, 14, 0)));
        List<Portal> portals = List.of(
                gate("to-ravine", "atrium", "ravine", "atrium-ravine", "ravine-arrival", "Reedbell water vista", 0),
                gate("ravine-home", "ravine", "atrium", "ravine-home", "atrium-return", "Warm central lantern", 0),
                gate("to-works", "atrium", "works", "atrium-works", "works-arrival", "Turning copper silhouettes", 2, "ravine-peak"),
                gate("works-home", "works", "atrium", "works-home", "atrium-return", "Warm central lantern", 0),
                gate("to-observatory", "atrium", "observatory", "atrium-observatory", "observatory-arrival",
                        "An indigo sky and pale dial", 5, "works-relay-done"),
                gate("observatory-home", "observatory", "atrium", "observatory-home", "atrium-return", "Warm central lantern", 0));
        List<Collectible> tokens = List.of(
                token("ravine-bank-token", "ravine", 4, 0, 8, false, "A lantern seed on the near bank."),
                token("ravine-bridge-token", "ravine", 14, 4, 20, false, "A lantern seed beside the bell bridge."),
                token("ravine-hidden-token", "ravine", -8, 2, 20, true, "Water muffles the lantern chime."),
                token("works-floor-token", "works", 6, 0, 8, false, "A lantern seed in the workshop court."),
                token("works-relay-token", "works", 24, 10, 16, false, "A lantern seed beside the relay."),
                token("works-hidden-token", "works", -10, 0, 20, true, "Amber light leaks beneath the hatch."),
                token("observatory-ramp-token", "observatory", 8, 4, 10, false, "A lantern seed on the ascent."),
                token("observatory-dial-token", "observatory", 20, 18, 18, false, "A lantern seed beside the moonseed dial."),
                token("observatory-hidden-token", "observatory", -12, 8, 16, true, "A dark star rings softly."));
        List<Objective> objectives = List.of(
                objective("atrium-arrival", "atrium", "Light the home lantern", Kind.VISIT),
                objective("atrium-view", "atrium", "See the three fragments", Kind.REACH, "atrium-overlook"),
                objective("ravine-visit", "ravine", "Follow the reedbell vista", Kind.VISIT),
                objective("ravine-peak", "ravine", "Ring the high bell", Kind.REACH, "ravine-summit"),
                objective("ravine-pair", "ravine", "Find the two path lantern seeds", Kind.COLLECT,
                        "ravine-bank-token", "ravine-bridge-token"),
                objective("ravine-secret", "ravine", "Find the quiet curtain", Kind.REACH, "ravine-curtain"),
                objective("works-visit", "works", "Enter the copper court", Kind.VISIT),
                objective("works-relay-done", "works", "Wake the relay lantern", Kind.REACH, "works-relay"),
                objective("works-pair", "works", "Find the two workshop lantern seeds", Kind.COLLECT,
                        "works-floor-token", "works-relay-token"),
                objective("works-secret", "works", "Open the amber service path", Kind.REACH, "works-hatch"),
                objective("observatory-visit", "observatory", "Reach the indigo terraces", Kind.VISIT),
                objective("observatory-dial", "observatory", "Align the moonseed dial", Kind.REACH, "observatory-zenith"),
                objective("observatory-pair", "observatory", "Find the two terrace lantern seeds", Kind.COLLECT,
                        "observatory-ramp-token", "observatory-dial-token"),
                objective("observatory-secret", "observatory", "Find the unlit star", Kind.REACH, "observatory-shutter"));
        return new ExplorationDefinition("lantern-reach", 1, "Lantern Reach", "atrium",
                List.of(atrium, ravine, works, observatory), portals, tokens, objectives, kit);
    }

    private static Point p(double x, double y, double z) { return new Point(x, y, z); }
    private static Marker marker(String id, double x, double y, double z, boolean secret, String hint) {
        return new Marker(id, p(x, y, z), secret, hint);
    }
    private static Placement place(String id, String module, double x, double y, double z, double yaw) {
        return new Placement(id, module, p(x, y, z), yaw);
    }
    private static Collectible token(String id, String world, double x, double y, double z, boolean secret, String hint) {
        return new Collectible(id, world, p(x, y, z), secret, hint);
    }
    private static Portal gate(String id, String from, String to, String marker, String landing, String visual,
                               int count, String... objectives) {
        return new Portal(id, from, to, marker, landing, visual, count, List.of(objectives));
    }
    private static Objective objective(String id, String world, String title, Kind kind, String... targets) {
        return new Objective(id, world, title, kind, List.of(targets), List.of());
    }
}
