// SPDX-License-Identifier: MIT
package com.daedalus.world.bricks;

import com.daedalus.world.BlockCoordinate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Objects;
import java.util.SplittableRandom;

/**
 * Optional Stud Relay practice rules over the existing ADR-034 obby. This is an original, invented
 * design extension: two corner studs per six-platform leg, checkpoint banking, and a clean-run ribbon.
 * It neither changes terrain nor awards inventory, experience, deeds, currency, or ranked times.
 * Landings are reports from a host, not proof that an avatar followed server-verified physics.
 */
public final class BricksRelay {
    public static final String VERSION = "bricks-stud-relay/v1";
    public static final int STUDS_PER_LEG = 2;
    public static final int LEGS = BricksOps.PLATFORMS / BricksOps.CHECKPOINT_EVERY;

    public enum Action { LAND, FALL, FINISH, RESTART }

    public enum Result {
        LANDED, STUD_COLLECTED, CHECKPOINT_BANKED, FELL, FINISHED, RESTARTED,
        OUT_OF_ORDER, OUTSIDE_LANDING, STUD_REQUIRED, COURSE_INCOMPLETE, ALREADY_FINISHED
    }

    /** A non-solid pickup resting on an existing platform; ids are stable for this course seed. */
    public record Stud(String id, int leg, int platform, BlockCoordinate at, String color) {
        public Stud {
            Objects.requireNonNull(id, "id");
            Objects.requireNonNull(at, "at");
            Objects.requireNonNull(color, "color");
        }
    }

    /** Only the obby metadata is retained, never the baseplate cube map. */
    public record Course(long seed, List<BricksOps.Platform> platforms, BricksOps.Platform finish, List<Stud> studs) {
        public Course {
            platforms = List.copyOf(platforms);
            studs = List.copyOf(studs);
            Objects.requireNonNull(finish, "finish");
            if (platforms.size() != BricksOps.PLATFORMS || studs.size() != LEGS * STUDS_PER_LEG) {
                throw new IllegalArgumentException("Relay requires the existing eighteen-platform Bricks course");
            }
        }
    }

    /** Immutable practice state. Stud bit positions are the course's sorted stud indexes. */
    public record State(long revision, int reachedPlatform, int checkpointPlatform, int collectedMask,
                        int bankedMask, int falls, long startedAtMillis, long completedAtMillis) {
        public boolean complete() {
            return completedAtMillis >= 0;
        }

        public long elapsedMillis(long nowMillis) {
            return Math.max(0, (complete() ? completedAtMillis : nowMillis) - startedAtMillis);
        }

        public boolean cleanRun() {
            return complete() && falls == 0;
        }
    }

    /** Platform is zero based, matching GET /world/{id}/obby; at is the cube the feet occupy. */
    public record Command(Action action, int platform, BlockCoordinate at) {
        public Command {
            Objects.requireNonNull(action, "action");
        }
    }

    public record Transition(Result result, State state) { }

    private BricksRelay() { }

    /** The same seed chooses the same six pickups without touching the original obby's random stream. */
    public static Course course(long seed, BricksOps.Plan plan) {
        Objects.requireNonNull(plan, "plan");
        SplittableRandom random = new SplittableRandom(seed ^ 0x5354554452454C41L);
        List<Stud> studs = new ArrayList<>();
        for (int leg = 0; leg < LEGS; leg++) {
            // Checkpoints are broad safe banks. Pickups live on two different earlier bricks in the leg.
            int first = random.nextInt(BricksOps.CHECKPOINT_EVERY - 1);
            int second = random.nextInt(BricksOps.CHECKPOINT_EVERY - 2);
            if (second >= first) {
                second++;
            }
            int[] offsets = {Math.min(first, second), Math.max(first, second)};
            for (int n = 0; n < offsets.length; n++) {
                int platform = leg * BricksOps.CHECKPOINT_EVERY + offsets[n];
                BricksOps.Platform p = plan.obby().get(platform);
                int x = random.nextBoolean() ? p.minX() : p.maxX();
                int z = random.nextBoolean() ? p.minZ() : p.maxZ();
                studs.add(new Stud("leg-" + (leg + 1) + "-stud-" + (n + 1), leg + 1, platform,
                        new BlockCoordinate(x, p.y() + 1, z), p.type().name()));
            }
        }
        studs.sort(Comparator.comparingInt(Stud::platform));
        return new Course(seed, plan.obby(), plan.finish(), studs);
    }

    public static State start(long nowMillis) {
        return new State(0, -1, -1, 0, 0, 0, nowMillis, -1);
    }

    /** Read-only respawn target for a host; the caller decides whether and how to move its avatar. */
    public static BlockCoordinate respawn(Course course, State state) {
        return state.checkpointPlatform() < 0 ? BricksOps.spawn()
                : course.platforms().get(state.checkpointPlatform()).standOn();
    }

    public static List<String> collectedStuds(Course course, int mask) {
        List<String> ids = new ArrayList<>();
        for (int i = 0; i < course.studs().size(); i++) {
            if ((mask & (1 << i)) != 0) {
                ids.add(course.studs().get(i).id());
            }
        }
        return List.copyOf(ids);
    }

    /** The next pickup, or null when every pickup is held or banked. Useful for non-color-only guidance. */
    public static Stud nextStud(Course course, State state) {
        for (int i = 0; i < course.studs().size(); i++) {
            if ((state.collectedMask() & (1 << i)) == 0) {
                return course.studs().get(i);
            }
        }
        return null;
    }

    /** Invalid reports leave state and revision unchanged. Accepted repeats never award a second stud. */
    public static Transition apply(Course course, State state, Command command, long nowMillis) {
        Objects.requireNonNull(course, "course");
        Objects.requireNonNull(state, "state");
        Objects.requireNonNull(command, "command");
        if (command.action() == Action.RESTART) {
            State fresh = start(nowMillis);
            return new Transition(Result.RESTARTED, new State(state.revision() + 1, fresh.reachedPlatform(),
                    fresh.checkpointPlatform(), 0, 0, 0, nowMillis, -1));
        }
        if (state.complete()) {
            return new Transition(Result.ALREADY_FINISHED, state);
        }
        return switch (command.action()) {
            case LAND -> land(course, state, command);
            case FALL -> new Transition(Result.FELL, new State(state.revision() + 1, state.checkpointPlatform(),
                    state.checkpointPlatform(), state.bankedMask(), state.bankedMask(), state.falls() + 1,
                    state.startedAtMillis(), -1));
            case FINISH -> finish(course, state, command.at(), nowMillis);
            default -> throw new IllegalArgumentException("Unsupported relay action");
        };
    }

    private static Transition land(Course course, State state, Command command) {
        int index = command.platform();
        if (index < 0 || index >= course.platforms().size()
                || (index != state.reachedPlatform() && index != state.reachedPlatform() + 1)) {
            return new Transition(Result.OUT_OF_ORDER, state);
        }
        BricksOps.Platform platform = course.platforms().get(index);
        if (!on(platform, command.at())) {
            return new Transition(Result.OUTSIDE_LANDING, state);
        }
        if (index > state.reachedPlatform() && missingOn(course, state, state.reachedPlatform())) {
            return new Transition(Result.STUD_REQUIRED, state);
        }
        int collected = state.collectedMask();
        for (int i = 0; i < course.studs().size(); i++) {
            Stud stud = course.studs().get(i);
            if (stud.platform() == index && stud.at().equals(command.at())) {
                collected |= 1 << i;
            }
        }
        int checkpoint = platform.checkpoint() ? index : state.checkpointPlatform();
        int banked = platform.checkpoint() ? collected : state.bankedMask();
        if (index == state.reachedPlatform() && collected == state.collectedMask() && banked == state.bankedMask()) {
            return new Transition(Result.LANDED, state);
        }
        Result result = platform.checkpoint() && checkpoint != state.checkpointPlatform() ? Result.CHECKPOINT_BANKED
                : collected != state.collectedMask() ? Result.STUD_COLLECTED : Result.LANDED;
        return new Transition(result, new State(state.revision() + 1, index, checkpoint, collected, banked,
                state.falls(), state.startedAtMillis(), -1));
    }

    private static boolean missingOn(Course course, State state, int platform) {
        for (int i = 0; i < course.studs().size(); i++) {
            if (course.studs().get(i).platform() == platform && (state.collectedMask() & (1 << i)) == 0) {
                return true;
            }
        }
        return false;
    }

    private static Transition finish(Course course, State state, BlockCoordinate at, long nowMillis) {
        int all = (1 << course.studs().size()) - 1;
        if (state.reachedPlatform() != course.platforms().size() - 1 || state.bankedMask() != all) {
            return new Transition(Result.COURSE_INCOMPLETE, state);
        }
        if (!on(course.finish(), at)) {
            return new Transition(Result.OUTSIDE_LANDING, state);
        }
        return new Transition(Result.FINISHED, new State(state.revision() + 1, state.reachedPlatform(),
                state.checkpointPlatform(), state.collectedMask(), state.bankedMask(), state.falls(),
                state.startedAtMillis(), Math.max(state.startedAtMillis(), nowMillis)));
    }

    private static boolean on(BricksOps.Platform platform, BlockCoordinate at) {
        return at != null && at.y() == platform.y() + 1 && at.x() >= platform.minX() && at.x() <= platform.maxX()
                && at.z() >= platform.minZ() && at.z() <= platform.maxZ();
    }
}
