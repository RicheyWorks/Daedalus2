// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Wood Wide Web (contest G82): under the regrown forest, fungal threads join the trees, and old mother trees feed the
 * shaded seedlings.
 *
 * <p>A seeded stand is a {@code width}×{@code height} grid of trees. Each tree is a MOTHER, a MATURE tree, a
 * SEEDLING or an empty cell. Every year each tree makes or needs carbon: mothers make {@code motherSurplus}, mature
 * trees make {@code matureSurplus}, and shaded seedlings need {@code seedlingNeed}. In a drought year (seeded, with
 * {@code droughtChance}) every tree makes {@code droughtCost} less.
 *
 * <p>Mycorrhizal threads join colonized trees that are orthogonal neighbours. Colonization spreads each year from a
 * colonized tree to each uncolonized neighbour with chance {@code spread}. Each connected network pools its carbon:
 * donors give what they hold above the starting store, and that pays the trees that would otherwise die, each just
 * enough to live. An unlinked tree stands alone. A tree whose
 * store falls below zero dies. A seedling that lives {@code seedlingYears} years becomes mature.
 *
 * <p>The player has spore inoculations ({@code spores}, each colonizes one tree) and the island needs timber. Logging
 * a mature tree gives 1 timber, a mother {@code motherTimber}. The quest is to meet {@code timberGoal} and still
 * raise {@code seedlingGoal} of the seedlings.
 */
public final class WoodWideWeb {

    /** A cell of the stand. */
    public enum Tree { EMPTY, SEEDLING, MATURE, MOTHER }

    /** What the stand became. */
    public enum Outcome { OLD_GROWTH, THINNED, COLLAPSED }

    /**
     * Stand tuning.
     *
     * @param width          stand width in cells
     * @param height         stand height in cells
     * @param years          years to run
     * @param motherChance   chance a seeded cell is a mother tree
     * @param matureChance   chance a seeded cell is a mature tree
     * @param seedlingChance chance a seeded cell is a seedling
     * @param motherSurplus  carbon a mother makes a year
     * @param matureSurplus  carbon a mature tree makes a year
     * @param seedlingNeed   carbon a shaded seedling needs a year
     * @param droughtChance  chance a year is a drought
     * @param droughtCost    carbon every tree loses in a drought year
     * @param startStore     carbon each tree starts with; donors keep this much back
     * @param spread         chance a colonized tree colonizes each bare neighbour a year
     * @param seedlingYears  years a seedling needs to become mature
     * @param spores         spore inoculations the player has
     * @param motherTimber   timber from logging a mother (a mature tree gives 1)
     * @param timberGoal     timber the island needs
     * @param seedlingGoal   share of the starting seedlings to raise
     */
    public record Settings(int width, int height, int years, double motherChance, double matureChance,
            double seedlingChance, double motherSurplus, double matureSurplus, double seedlingNeed,
            double droughtChance, double droughtCost, double startStore, double spread, int seedlingYears,
            int spores, int motherTimber, int timberGoal, double seedlingGoal) {

        /** The default stand. */
        public static final Settings DEFAULT = new Settings(8, 8, 12, 0.08, 0.35, 0.2, 4.0, 1.0, 1.0, 0.3, 1.0,
                2.0, 0.5, 5, 6, 3, 10, 0.6);

        /** Rejects a stand that cannot run. */
        public Settings {
            if (width < 1 || height < 1 || years < 1 || !(motherChance >= 0) || !(matureChance >= 0)
                    || !(seedlingChance >= 0) || !(motherChance + matureChance + seedlingChance <= 1)
                    || !(motherSurplus >= 0) || !(matureSurplus >= 0) || !(seedlingNeed >= 0)
                    || !(droughtChance >= 0 && droughtChance <= 1) || !(droughtCost >= 0) || !(startStore >= 0)
                    || !(spread >= 0 && spread <= 1) || seedlingYears < 1 || spores < 0 || motherTimber < 0
                    || timberGoal < 0 || !(seedlingGoal >= 0 && seedlingGoal <= 1)) {
                throw new IllegalArgumentException("bad wood wide web settings");
            }
        }
    }

    /** One year. */
    public record Year(int index, boolean drought, int networks, int linkedTrees, int seedlings, int deaths) {}

    /**
     * The result.
     *
     * @param outcome      what the stand became
     * @param timber       timber logged
     * @param seedlingsRaised seedlings that grew to mature (or still live at the end)
     * @param seedlingsStart  seedlings at the start
     * @param stand        the final stand, row by row
     * @param years        one row per year
     */
    public record Report(Outcome outcome, int timber, int seedlingsRaised, int seedlingsStart, List<Tree> stand,
            List<Year> years) {

        /** Defensive copies. */
        public Report {
            stand = List.copyOf(stand);
            years = List.copyOf(years);
        }

        /** Raised fraction of the starting seedlings. */
        public double raisedShare() {
            return seedlingsStart == 0 ? 0 : (double) seedlingsRaised / seedlingsStart;
        }

        /** The stand cell as a BattlefieldEcology band: OAK for mothers, PINE for mature, SCRUB for seedlings. */
        public Vegetation band(int index) {
            return switch (stand.get(index)) {
                case MOTHER -> Vegetation.OAK;
                case MATURE -> Vegetation.PINE;
                case SEEDLING -> Vegetation.SCRUB;
                case EMPTY -> Vegetation.MEADOW;
            };
        }
    }

    private final Settings s;
    private final long seed;
    private final Tree[] tree;
    private final boolean[] colonized;
    private final boolean[] logged;
    private int sporesUsed;

    private WoodWideWeb(Settings s, long seed) {
        this.s = s;
        this.seed = seed;
        int n = s.width() * s.height();
        tree = new Tree[n];
        colonized = new boolean[n];
        logged = new boolean[n];
        SplittableRandom rng = new SplittableRandom(seed);
        for (int i = 0; i < n; i++) {
            double u = rng.nextDouble();
            tree[i] = u < s.motherChance() ? Tree.MOTHER
                    : u < s.motherChance() + s.matureChance() ? Tree.MATURE
                    : u < s.motherChance() + s.matureChance() + s.seedlingChance() ? Tree.SEEDLING : Tree.EMPTY;
            colonized[i] = tree[i] == Tree.MOTHER || (tree[i] == Tree.MATURE && rng.nextDouble() < 0.5);
        }
    }

    /**
     * A hand-planted stand for quests and tests. Rows are separated by {@code /}. Use {@code M} for a mother
     * (colonized), {@code T} for a colonized mature tree, {@code t} for a bare mature tree, {@code S} for a seedling and
     * {@code .} for an empty cell. The settings' width and height must match.
     */
    public static WoodWideWeb planted(Settings settings, long seed, String rows) {
        if (settings == null || rows == null) {
            throw new IllegalArgumentException("settings and rows");
        }
        String[] r = rows.split("/", -1);
        if (r.length != settings.height()) {
            throw new IllegalArgumentException("rows do not match the stand height");
        }
        WoodWideWeb w = new WoodWideWeb(settings, seed);
        for (int y = 0; y < r.length; y++) {
            if (r[y].length() != settings.width()) {
                throw new IllegalArgumentException("row " + y + " does not match the stand width");
            }
            for (int x = 0; x < r[y].length(); x++) {
                int i = y * settings.width() + x;
                char c = r[y].charAt(x);
                w.tree[i] = switch (c) {
                    case 'M' -> Tree.MOTHER;
                    case 'T', 't' -> Tree.MATURE;
                    case 'S' -> Tree.SEEDLING;
                    case '.' -> Tree.EMPTY;
                    default -> throw new IllegalArgumentException("unknown cell " + c);
                };
                w.colonized[i] = c == 'M' || c == 'T';
            }
        }
        return w;
    }

    /** A seeded stand. Mother trees start colonized (the fungus lives on their old roots), and half the mature trees. */
    public static WoodWideWeb stand(Settings settings, long seed) {
        if (settings == null) {
            throw new IllegalArgumentException("settings");
        }
        return new WoodWideWeb(settings, seed);
    }

    /** The tree at (x, y) before the run. */
    public Tree at(int x, int y) {
        return tree[index(x, y)];
    }

    /** Whether the tree at (x, y) is colonized before the run. */
    public boolean colonized(int x, int y) {
        return colonized[index(x, y)];
    }

    /** Inoculate the tree at (x, y) with spores. False if empty, already colonized, logged or out of spores. */
    public boolean inoculate(int x, int y) {
        int i = index(x, y);
        if (tree[i] == Tree.EMPTY || colonized[i] || logged[i] || sporesUsed >= s.spores()) {
            return false;
        }
        colonized[i] = true;
        sporesUsed++;
        return true;
    }

    /** Log the tree at (x, y) before the run. False for seedlings, empty cells or a tree already marked. */
    public boolean log(int x, int y) {
        int i = index(x, y);
        if (logged[i] || (tree[i] != Tree.MATURE && tree[i] != Tree.MOTHER)) {
            return false;
        }
        logged[i] = true;
        return true;
    }

    /** Spores left. */
    public int sporesLeft() {
        return s.spores() - sporesUsed;
    }

    /** Runs the stand. Deterministic in the settings, the seed and the plan. */
    public Report run() {
        int n = tree.length;
        Tree[] t = tree.clone();
        boolean[] col = colonized.clone();
        double[] store = new double[n];
        int[] age = new int[n];
        int timber = 0;
        int seedlingsStart = 0;
        for (int i = 0; i < n; i++) {
            if (logged[i]) {
                timber += t[i] == Tree.MOTHER ? s.motherTimber() : 1;
                t[i] = Tree.EMPTY;
                col[i] = false;
            }
            if (t[i] == Tree.SEEDLING) {
                seedlingsStart++;
            }
            store[i] = s.startStore();
        }
        int raised = 0;
        List<Year> log = new ArrayList<>();
        for (int y = 0; y < s.years(); y++) {
            boolean drought = roll(y, -1) < s.droughtChance();
            boolean[] grow = new boolean[n];
            for (int i = 0; i < n; i++) {
                if (col[i]) {
                    for (int j : neighbours(i)) {
                        if (t[j] != Tree.EMPTY && !col[j] && roll(y, i * n + j) < s.spread()) {
                            grow[j] = true;
                        }
                    }
                }
            }
            for (int i = 0; i < n; i++) {
                col[i] |= grow[i];
            }
            double[] net = new double[n];
            for (int i = 0; i < n; i++) {
                net[i] = switch (t[i]) {
                    case MOTHER -> s.motherSurplus();
                    case MATURE -> s.matureSurplus();
                    case SEEDLING -> -s.seedlingNeed();
                    case EMPTY -> 0;
                } - (drought && t[i] != Tree.EMPTY ? s.droughtCost() : 0);
            }
            int[] comp = new int[n];
            java.util.Arrays.fill(comp, -1);
            int networks = 0;
            int linked = 0;
            for (int i = 0; i < n; i++) {
                if (t[i] == Tree.EMPTY || !col[i] || comp[i] >= 0) {
                    continue;
                }
                List<Integer> members = new ArrayList<>();
                java.util.ArrayDeque<Integer> q = new java.util.ArrayDeque<>();
                q.add(i);
                comp[i] = networks;
                while (!q.isEmpty()) {
                    int c = q.poll();
                    members.add(c);
                    for (int j : neighbours(c)) {
                        if (t[j] != Tree.EMPTY && col[j] && comp[j] < 0) {
                            comp[j] = networks;
                            q.add(j);
                        }
                    }
                }
                networks++;
                if (members.size() > 1) {
                    linked += members.size();
                    share(members, net, store, s.startStore());
                } else {
                    store[i] += net[i];
                }
            }
            for (int i = 0; i < n; i++) {
                if (t[i] != Tree.EMPTY && comp[i] < 0) {
                    store[i] += net[i];
                }
            }
            int deaths = 0;
            int seedlings = 0;
            for (int i = 0; i < n; i++) {
                if (t[i] == Tree.EMPTY) {
                    continue;
                }
                if (store[i] < 0) {
                    t[i] = Tree.EMPTY;
                    col[i] = false;
                    deaths++;
                    continue;
                }
                if (t[i] == Tree.SEEDLING) {
                    age[i]++;
                    if (age[i] >= s.seedlingYears()) {
                        t[i] = Tree.MATURE;
                        raised++;
                    } else {
                        seedlings++;
                    }
                }
            }
            log.add(new Year(y, drought, networks, linked, seedlings, deaths));
        }
        for (Tree x : t) {
            if (x == Tree.SEEDLING) {
                raised++;
            }
        }
        double share = seedlingsStart == 0 ? 0 : (double) raised / seedlingsStart;
        boolean anyMother = false;
        int alive = 0;
        for (Tree x : t) {
            anyMother |= x == Tree.MOTHER;
            alive += x == Tree.EMPTY ? 0 : 1;
        }
        Outcome outcome = alive == 0 || (seedlingsStart > 0 && raised == 0) ? Outcome.COLLAPSED
                : share >= s.seedlingGoal() && timber >= s.timberGoal() && anyMother ? Outcome.OLD_GROWTH
                : Outcome.THINNED;
        return new Report(outcome, timber, raised, seedlingsStart, List.of(t), log);
    }

    /** A fixed draw per (year, key): the plan never shifts the dice for other cells. */
    private double roll(int year, long key) {
        long z = seed + 0x9E3779B97F4A7C15L * (year + 1) + 0xBF58476D1CE4E5B9L * (key + 2);
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        z = z ^ (z >>> 31);
        return (z >>> 11) * 0x1.0p-53;
    }

    /**
     * One network's year: every tree first books its own carbon. Donors (trees above {@code reserve}) give what they
     * hold above it, and that pool pays the trees that would die, lowest index first, each just enough to live. A
     * network never lets two die to half-save both.
     */
    private static void share(List<Integer> members, double[] net, double[] store, double reserve) {
        double pool = 0;
        for (int i : members) {
            store[i] += net[i];
            pool += Math.max(0, store[i] - reserve);
        }
        double given = 0;
        for (int i : members) {
            if (store[i] < 0 && given - store[i] <= pool) {
                given -= store[i];
                store[i] = 0;
            }
        }
        if (given > 0) {
            for (int i : members) {
                double spare = store[i] - reserve;
                if (spare > 0) {
                    store[i] -= given * spare / pool;
                }
            }
        }
    }

    private List<Integer> neighbours(int i) {
        int x = i % s.width();
        int y = i / s.width();
        List<Integer> out = new ArrayList<>(4);
        if (x > 0) {
            out.add(i - 1);
        }
        if (x + 1 < s.width()) {
            out.add(i + 1);
        }
        if (y > 0) {
            out.add(i - s.width());
        }
        if (y + 1 < s.height()) {
            out.add(i + s.width());
        }
        return out;
    }

    private int index(int x, int y) {
        if (x < 0 || y < 0 || x >= s.width() || y >= s.height()) {
            throw new IllegalArgumentException("cell out of the stand");
        }
        return y * s.width() + x;
    }
}
