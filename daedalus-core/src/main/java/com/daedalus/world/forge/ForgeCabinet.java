// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Random;
import java.util.function.Function;
import java.util.function.Predicate;

/**
 * Forge Cabinet: one playable arcade cabinet on Hephaestus Island that bundles the forge math games into a single
 * menu. Each cabinet slot wraps one forge tool: it deals a seeded puzzle, grades the player's answer with that tool's
 * own grader, and answers with the tool's Forgemaster line. A {@link Session} runs the play loop (pick a game, get a
 * puzzle, submit, score and streak) and reports to the quest hook {@link #QUEST_ID}.
 *
 * <p>Games are registered in a modular registry ({@link #registry()}); adding a game is one {@link Game} entry.
 */
public final class ForgeCabinet {

    /** Keith numbers up to 200000, built once on first use of the Keith Kindling slot. */
    private static final class KeithList {
        static final List<Long> KEITH = Collections.unmodifiableList(KeithKindling.keithUpTo(200_000));

        private KeithList() {
        }
    }

    /** Quest id for the Hephaestus Island forge cabinet hook. */
    public static final String QUEST_ID = "q_forge_cabinet";
    /** Points for a correct answer before streak bonus. */
    public static final int BASE_POINTS = 10;
    /** Largest streak bonus multiplier. */
    public static final int MAX_STREAK_BONUS = 5;

    private static final Map<String, Game> REGISTRY = buildRegistry();

    private ForgeCabinet() {
    }

    /** One dealt puzzle: the prompt, a reference answer, and a checker backed by the game's own grader. */
    public static final class Puzzle {
        private final String gameId;
        private final String prompt;
        private final String reference;
        private final Predicate<String> checker;

        Puzzle(String gameId, String prompt, String reference, Predicate<String> checker) {
            this.gameId = gameId;
            this.prompt = prompt;
            this.reference = reference;
            this.checker = checker;
        }

        /** Game id that dealt this puzzle. */
        public String gameId() {
            return gameId;
        }

        /** Question shown to the player. */
        public String prompt() {
            return prompt;
        }

        /** One accepted answer (other equivalent answers may also pass). */
        public String reference() {
            return reference;
        }

        /** True when the answer passes the game's grader; malformed answers fail. */
        public boolean check(String answer) {
            if (answer == null) {
                return false;
            }
            try {
                return checker.test(answer.trim().toLowerCase(Locale.ROOT).replace(" ", ""));
            } catch (RuntimeException e) {
                return false;
            }
        }
    }

    /** A cabinet slot. */
    public static final class Game {
        private final String id;
        private final String title;
        private final String toolQuest;
        private final Function<Random, Puzzle> dealer;
        private final String turned;
        private final String slipped;

        Game(String id, String title, String toolQuest, Function<Random, Puzzle> dealer, String turned,
            String slipped) {
            this.id = id;
            this.title = title;
            this.toolQuest = toolQuest;
            this.dealer = dealer;
            this.turned = turned;
            this.slipped = slipped;
        }

        /** Stable slot id. */
        public String id() {
            return id;
        }

        /** Menu title. */
        public String title() {
            return title;
        }

        /** Quest id of the wrapped forge tool. */
        public String toolQuest() {
            return toolQuest;
        }

        /** Deal a puzzle from the given random source. */
        public Puzzle deal(Random rng) {
            return dealer.apply(rng);
        }

        /** Forgemaster line for a result. */
        public String line(boolean correct) {
            return correct ? turned : slipped;
        }
    }

    /** Outcome of one submitted answer. */
    public record Result(String gameId, boolean correct, String reference, String line, int points, int streak,
        int score) {
    }

    private static long[] pair(String s) {
        String[] p = s.split(",");
        if (p.length != 2) {
            throw new IllegalArgumentException("need a,b");
        }
        return new long[] {Long.parseLong(p[0]), Long.parseLong(p[1])};
    }

    private static Game game(String id, String title, String quest, Function<Random, Puzzle> dealer,
        String turned, String slipped) {
        return new Game(id, title, quest, dealer, turned, slipped);
    }

    private static int smallPrime(Random r, int lo, int hi) {
        while (true) {
            int p = lo + r.nextInt(hi - lo + 1);
            if (MersenneBellows.isPrimeInt(p)) {
                return p;
            }
        }
    }

    private static Map<String, Game> buildRegistry() {
        List<Game> g = new ArrayList<>();
        g.add(game("carmichael", "Carmichael Cycle", CarmichaelCycle.QUEST_ID, r -> {
            long n = 2 + r.nextInt(5000);
            return new Puzzle("carmichael", "Universal cycle lambda(" + n + ")?", Long.toString(
                CarmichaelCycle.lambda(n)), a -> CarmichaelCycle.grade(n, Long.parseLong(a))
                == CarmichaelCycle.Grade.TURNED);
        }, CarmichaelCycle.forgemasterLine(CarmichaelCycle.Grade.TURNED),
            CarmichaelCycle.forgemasterLine(CarmichaelCycle.Grade.SLIPPED)));
        g.add(game("gaussian", "Gaussian Gears", GaussianGears.QUEST_ID, r -> {
            long n;
            long[] s;
            do {
                n = 1 + r.nextInt(10_000);
                s = GaussianGears.twoSquares(n);
            } while (s.length == 0);
            long fn = n;
            return new Puzzle("gaussian", "Split rim " + n + " as a,b with a^2+b^2=" + n, s[0] + "," + s[1],
                a -> {
                    long[] p = pair(a);
                    return GaussianGears.grade(fn, p[0], p[1]) == GaussianGears.Grade.TURNED;
                });
        }, GaussianGears.forgemasterLine(GaussianGears.Grade.TURNED),
            GaussianGears.forgemasterLine(GaussianGears.Grade.SLIPPED)));
        g.add(game("faulhaber", "Faulhaber Furnace", FaulhaberFurnace.QUEST_ID, r -> {
            int k = 1 + r.nextInt(6);
            long n = 1 + r.nextInt(50);
            return new Puzzle("faulhaber", "1^" + k + "+...+" + n + "^" + k + "?", FaulhaberFurnace.powerSum(k, n)
                .toString(), a -> FaulhaberFurnace.grade(k, n, new BigInteger(a)) == FaulhaberFurnace.Grade.TURNED);
        }, FaulhaberFurnace.forgemasterLine(FaulhaberFurnace.Grade.TURNED),
            FaulhaberFurnace.forgemasterLine(FaulhaberFurnace.Grade.SLIPPED)));
        g.add(game("mersenne", "Mersenne Bellows", MersenneBellows.QUEST_ID, r -> {
            int p = smallPrime(r, 2, 130);
            return new Puzzle("mersenne", "Is 2^" + p + "-1 prime or composite?", MersenneBellows.isMersennePrime(p)
                ? "prime" : "composite", a -> {
                    if (!"prime".equals(a) && !"composite".equals(a)) {
                        return false;
                    }
                    return MersenneBellows.grade(p, "prime".equals(a)) == MersenneBellows.Grade.TURNED;
                });
        }, MersenneBellows.forgemasterLine(MersenneBellows.Grade.TURNED),
            MersenneBellows.forgemasterLine(MersenneBellows.Grade.SLIPPED)));
        g.add(game("lucas", "Lucas Lattice", LucasLattice.QUEST_ID, r -> {
            long n = r.nextInt(1_000_001);
            long k = n == 0 ? 0 : (long) (r.nextDouble() * (n + 1));
            int[] ps = {2, 3, 5, 7, 11, 13};
            long p = ps[r.nextInt(ps.length)];
            return new Puzzle("lucas", "C(" + n + "," + k + ") mod " + p + "?", Long.toString(
                LucasLattice.binomialMod(n, k, p)), a -> LucasLattice.grade(n, k, p, Long.parseLong(a))
                == LucasLattice.Grade.TURNED);
        }, LucasLattice.forgemasterLine(LucasLattice.Grade.TURNED),
            LucasLattice.forgemasterLine(LucasLattice.Grade.SLIPPED)));
        g.add(game("frobenius", "Frobenius Fittings", FrobeniusFittings.QUEST_ID, r -> {
            long a;
            long b;
            do {
                a = 3 + r.nextInt(28);
                b = 3 + r.nextInt(28);
            } while (a == b || FrobeniusFittings.gcd(a, b) != 1);
            long[] packs = {a, b};
            return new Puzzle("frobenius", "Largest order no mix of packs " + a + " and " + b + " fills?",
                Long.toString(FrobeniusFittings.frobenius(packs)), s -> FrobeniusFittings.grade(packs,
                Long.parseLong(s)) == FrobeniusFittings.Grade.TURNED);
        }, FrobeniusFittings.forgemasterLine(FrobeniusFittings.Grade.TURNED),
            FrobeniusFittings.forgemasterLine(FrobeniusFittings.Grade.SLIPPED)));
        g.add(game("legendre", "Legendre Ladle", LegendreLadle.QUEST_ID, r -> {
            long n = r.nextInt(1001);
            long b = 2 + r.nextInt(19);
            return new Puzzle("legendre", "Trailing zeros of " + n + "! in base " + b + "?", Long.toString(
                LegendreLadle.trailingZeros(n, b)), a -> LegendreLadle.grade(n, b, Long.parseLong(a))
                == LegendreLadle.Grade.TURNED);
        }, LegendreLadle.forgemasterLine(LegendreLadle.Grade.TURNED),
            LegendreLadle.forgemasterLine(LegendreLadle.Grade.SLIPPED)));
        g.add(game("fermat", "Fermat Fold", FermatFold.QUEST_ID, r -> {
            long n = (3 + 2L * r.nextInt(150)) * (3 + 2L * r.nextInt(150));
            long[] f = FermatFold.fold(n, FermatFold.MAX_STEPS);
            return new Puzzle("fermat", "Fold " + n + " grains into a,b nearest square", f[0] + "," + f[1], a -> {
                long[] p = pair(a);
                return FermatFold.grade(n, p[0], p[1]) == FermatFold.Grade.TURNED;
            });
        }, FermatFold.forgemasterLine(FermatFold.Grade.TURNED),
            FermatFold.forgemasterLine(FermatFold.Grade.SLIPPED)));
        g.add(game("liouville", "Liouville Lanterns", LiouvilleLanterns.QUEST_ID, r -> {
            long n = 1 + r.nextInt(1_000_000);
            return new Puzzle("liouville", "Shade of lantern " + n + " (1 bright, -1 dark)?", Integer.toString(
                LiouvilleLanterns.lambda(n)), a -> LiouvilleLanterns.grade(n, Integer.parseInt(a))
                == LiouvilleLanterns.Grade.TURNED);
        }, LiouvilleLanterns.forgemasterLine(LiouvilleLanterns.Grade.TURNED),
            LiouvilleLanterns.forgemasterLine(LiouvilleLanterns.Grade.SLIPPED)));
        g.add(game("ramanujan", "Ramanujan Rings", RamanujanRings.QUEST_ID, r -> {
            long q = 1 + r.nextInt(60);
            long n = r.nextInt(101);
            return new Puzzle("ramanujan", "Echo c_" + q + "(" + n + ")?", Long.toString(
                RamanujanRings.ramanujanSum(q, n)), a -> RamanujanRings.grade(q, n, Long.parseLong(a))
                == RamanujanRings.Grade.TURNED);
        }, RamanujanRings.forgemasterLine(RamanujanRings.Grade.TURNED),
            RamanujanRings.forgemasterLine(RamanujanRings.Grade.SLIPPED)));
        g.add(game("dedekind", "Dedekind Dials", DedekindDials.QUEST_ID, r -> {
            long k = 2 + r.nextInt(49);
            long h = 1 + r.nextInt((int) k);
            BigInteger[] s = DedekindDials.dedekindSum(h, k);
            return new Puzzle("dedekind", "Dedekind sum s(" + h + "," + k + ") as num/den?", s[0] + "/" + s[1],
                a -> {
                    String[] p = a.split("/");
                    long num = Long.parseLong(p[0]);
                    long den = p.length == 1 ? 1 : Long.parseLong(p[1]);
                    return p.length <= 2 && DedekindDials.grade(h, k, num, den) == DedekindDials.Grade.TURNED;
                });
        }, DedekindDials.forgemasterLine(DedekindDials.Grade.TURNED),
            DedekindDials.forgemasterLine(DedekindDials.Grade.SLIPPED)));
        g.add(game("harshad", "Harshad Hammers", HarshadHammers.QUEST_ID, r -> {
            long n = 1 + r.nextInt(5000);
            return new Puzzle("harshad", "Clean (Harshad) hammers in 1.." + n + "?", Long.toString(
                HarshadHammers.countHarshad(n)), a -> HarshadHammers.grade(n, Long.parseLong(a))
                == HarshadHammers.Grade.TURNED);
        }, HarshadHammers.forgemasterLine(HarshadHammers.Grade.TURNED),
            HarshadHammers.forgemasterLine(HarshadHammers.Grade.SLIPPED)));
        g.add(game("subset", "Subset Smelter", SubsetSmelter.QUEST_ID, r -> {
            long[] f = new long[8];
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < 8; i++) {
                f[i] = r.nextInt(10);
                sb.append(i == 0 ? "" : " ").append(f[i]);
            }
            int s = r.nextInt(8);
            return new Puzzle("subset", "Yields [" + sb + "] by mask 0..7; total over sub-alloys of mask " + s + "?",
                Long.toString(SubsetSmelter.zeta(f)[s]), a -> SubsetSmelter.grade(f, s, Long.parseLong(a))
                == SubsetSmelter.Grade.TURNED);
        }, SubsetSmelter.forgemasterLine(SubsetSmelter.Grade.TURNED),
            SubsetSmelter.forgemasterLine(SubsetSmelter.Grade.SLIPPED)));
        g.add(game("automorph", "Automorph Anvil", AutomorphAnvil.QUEST_ID, r -> {
            int k = 1 + r.nextInt(8);
            BigInteger t = AutomorphAnvil.tails(k)[1];
            return new Puzzle("automorph", "The " + k + "-digit automorphic tail ending in 6?", t.toString(),
                a -> new BigInteger(a).equals(t));
        }, AutomorphAnvil.forgemasterLine(AutomorphAnvil.Grade.TURNED),
            AutomorphAnvil.forgemasterLine(AutomorphAnvil.Grade.SLIPPED)));
        g.add(game("smith", "Smith Stamps", SmithStamps.QUEST_ID, r -> {
            long n = 4 + r.nextInt(20_000);
            if (r.nextBoolean()) {
                while (!SmithStamps.isSmith(n)) {
                    n++;
                }
            }
            long fn = n;
            return new Puzzle("smith", "Is stamp " + n + " a Smith number? (smith/plain)", SmithStamps.isSmith(n)
                ? "smith" : "plain", a -> {
                    if (!"smith".equals(a) && !"plain".equals(a)) {
                        return false;
                    }
                    return SmithStamps.grade(fn, "smith".equals(a)) == SmithStamps.Grade.TURNED;
                });
        }, SmithStamps.forgemasterLine(SmithStamps.Grade.TURNED),
            SmithStamps.forgemasterLine(SmithStamps.Grade.SLIPPED)));
        g.add(game("practical", "Practical Weights", PracticalWeights.QUEST_ID, r -> {
            long n = 2 + r.nextInt(20_000);
            if (r.nextBoolean()) {
                while (!PracticalWeights.isPractical(n)) {
                    n++;
                }
            }
            long fn = n;
            return new Puzzle("practical", "Do the divisors of " + n + " weigh every load below it? (practical/short)",
                PracticalWeights.isPractical(n) ? "practical" : "short", a -> {
                    if (!"practical".equals(a) && !"short".equals(a)) {
                        return false;
                    }
                    return PracticalWeights.grade(fn, "practical".equals(a)) == PracticalWeights.Grade.WEIGHED;
                });
        }, PracticalWeights.forgemasterLine(PracticalWeights.Grade.WEIGHED),
            PracticalWeights.forgemasterLine(PracticalWeights.Grade.SHORT)));
        g.add(game("record", "Record Ingots", RecordIngots.QUEST_ID, r -> {
            long n = 1 + r.nextInt(50_000);
            if (r.nextBoolean()) {
                while (!RecordIngots.isRecord(n)) {
                    n++;
                }
            }
            long fn = n;
            return new Puzzle("record", "Does ingot " + n + " split more ways than every smaller one? (record/common)",
                RecordIngots.isRecord(n) ? "record" : "common", a -> {
                    if (!"record".equals(a) && !"common".equals(a)) {
                        return false;
                    }
                    return RecordIngots.grade(fn, "record".equals(a)) == RecordIngots.Grade.TURNED;
                });
        }, RecordIngots.forgemasterLine(RecordIngots.Grade.TURNED),
            RecordIngots.forgemasterLine(RecordIngots.Grade.SLIPPED)));
        g.add(game("achilles", "Achilles Rivets", AchillesRivets.QUEST_ID, r -> {
            long n = 1 + r.nextInt(100_000);
            if (r.nextBoolean()) {
                while (!AchillesRivets.isAchilles(n)) {
                    n++;
                }
            }
            long fn = n;
            return new Puzzle("achilles", "Is rivet count " + n + " powerful but no perfect power? (achilles/brittle)",
                AchillesRivets.isAchilles(n) ? "achilles" : "brittle", a -> {
                    if (!"achilles".equals(a) && !"brittle".equals(a)) {
                        return false;
                    }
                    return AchillesRivets.grade(fn, "achilles".equals(a)) == AchillesRivets.Grade.TURNED;
                });
        }, AchillesRivets.forgemasterLine(AchillesRivets.Grade.TURNED),
            AchillesRivets.forgemasterLine(AchillesRivets.Grade.SLIPPED)));
        g.add(game("weird", "Weird Hoards", WeirdHoards.QUEST_ID, r -> {
            long n = 1 + r.nextInt(15_000);
            if (r.nextBoolean()) {
                List<Long> w = WeirdHoards.weirdUpTo(15_000);
                n = w.get(r.nextInt(w.size()));
            }
            long fn = n;
            return new Puzzle("weird", "Is hoard " + n + " abundant with no exact handful? (weird/tame)",
                WeirdHoards.isWeird(n) ? "weird" : "tame", a -> {
                    if (!"weird".equals(a) && !"tame".equals(a)) {
                        return false;
                    }
                    return WeirdHoards.grade(fn, "weird".equals(a)) == WeirdHoards.Grade.TURNED;
                });
        }, WeirdHoards.forgemasterLine(WeirdHoards.Grade.TURNED),
            WeirdHoards.forgemasterLine(WeirdHoards.Grade.SLIPPED)));
        g.add(game("untouched", "Untouched Brands", UntouchedBrands.QUEST_ID, r -> {
            long n = 1 + r.nextInt(UntouchedBrands.MAX_BRAND);
            if (r.nextBoolean()) {
                List<Long> u = UntouchedBrands.untouchedUpTo(UntouchedBrands.MAX_BRAND);
                n = u.get(r.nextInt(u.size()));
            }
            long fn = n;
            return new Puzzle("untouched", "Is brand " + n + " the aliquot sum of no ingot? (untouched/touched)",
                UntouchedBrands.isUntouched(n) ? "untouched" : "touched", a -> {
                    if (!"untouched".equals(a) && !"touched".equals(a)) {
                        return false;
                    }
                    return UntouchedBrands.grade(fn, "untouched".equals(a)) == UntouchedBrands.Grade.TURNED;
                });
        }, UntouchedBrands.forgemasterLine(UntouchedBrands.Grade.TURNED),
            UntouchedBrands.forgemasterLine(UntouchedBrands.Grade.SLIPPED)));
        g.add(game("ludic", "Ludic Lots", LudicLots.QUEST_ID, r -> {
            int n = 1 + r.nextInt(20_000);
            if (r.nextBoolean()) {
                while (!LudicLots.isLudic(n)) {
                    n++;
                }
            }
            int fn = n;
            return new Puzzle("ludic", "Does lot " + n + " survive the ludic cull? (ludic/culled)",
                LudicLots.isLudic(n) ? "ludic" : "culled", a -> {
                    if (!"ludic".equals(a) && !"culled".equals(a)) {
                        return false;
                    }
                    return LudicLots.grade(fn, "ludic".equals(a)) == LudicLots.Grade.TURNED;
                });
        }, LudicLots.forgemasterLine(LudicLots.Grade.TURNED),
            LudicLots.forgemasterLine(LudicLots.Grade.SLIPPED)));
        g.add(game("keith", "Keith Kindling", KeithKindling.QUEST_ID, r -> {
            long n = 10 + r.nextInt(100_000);
            if (r.nextBoolean()) {
                List<Long> k = KeithList.KEITH;
                n = k.get(r.nextInt(k.size()));
            }
            long fn = n;
            return new Puzzle("keith", "Does ember " + n + "'s digit chain reach it exactly? (keith/cold)",
                KeithKindling.isKeith(n) ? "keith" : "cold", a -> {
                    if (!"keith".equals(a) && !"cold".equals(a)) {
                        return false;
                    }
                    return KeithKindling.grade(fn, "keith".equals(a)) == KeithKindling.Grade.TURNED;
                });
        }, KeithKindling.forgemasterLine(KeithKindling.Grade.TURNED),
            KeithKindling.forgemasterLine(KeithKindling.Grade.SLIPPED)));
        g.add(game("self", "Self Forged", SelfForged.QUEST_ID, r -> {
            long n = 1 + r.nextInt(100_000);
            if (r.nextBoolean()) {
                while (!SelfForged.isSelf(n)) {
                    n++;
                }
            }
            long fn = n;
            return new Puzzle("self", "Can no blank m stamp m + digitSum(m) = " + n + "? (self/stamped)",
                SelfForged.isSelf(n) ? "self" : "stamped", a -> {
                    if (!"self".equals(a) && !"stamped".equals(a)) {
                        return false;
                    }
                    return SelfForged.grade(fn, "self".equals(a)) == SelfForged.Grade.TURNED;
                });
        }, SelfForged.forgemasterLine(SelfForged.Grade.TURNED),
            SelfForged.forgemasterLine(SelfForged.Grade.SLIPPED)));
        g.add(game("triad", "Triad Alloys", TriadAlloys.QUEST_ID, r -> {
            long n = 1 + r.nextInt(100_000);
            if (r.nextBoolean()) {
                while (!TriadAlloys.isSphenic(n)) {
                    n++;
                }
            }
            long fn = n;
            return new Puzzle("triad", "Is alloy " + n + " three distinct prime ores, each once? (triad/mixed)",
                TriadAlloys.isSphenic(n) ? "triad" : "mixed", a -> {
                    if (!"triad".equals(a) && !"mixed".equals(a)) {
                        return false;
                    }
                    return TriadAlloys.grade(fn, "triad".equals(a)) == TriadAlloys.Grade.TURNED;
                });
        }, TriadAlloys.forgemasterLine(TriadAlloys.Grade.TURNED),
            TriadAlloys.forgemasterLine(TriadAlloys.Grade.SLIPPED)));
        g.add(game("pernicious", "Pernicious Pins", PerniciousPins.QUEST_ID, r -> {
            long n = r.nextInt(1 << 20);
            long fn = n;
            return new Puzzle("pernicious", "Is the count of set bits in pin " + n + " prime? (pernicious/plainpin)",
                PerniciousPins.isPernicious(n) ? "pernicious" : "plainpin", a -> {
                    if (!"pernicious".equals(a) && !"plainpin".equals(a)) {
                        return false;
                    }
                    return PerniciousPins.grade(fn, "pernicious".equals(a)) == PerniciousPins.Grade.TURNED;
                });
        }, PerniciousPins.forgemasterLine(PerniciousPins.Grade.TURNED),
            PerniciousPins.forgemasterLine(PerniciousPins.Grade.SLIPPED)));
        g.add(game("polite", "Polite Stacks", PoliteStacks.QUEST_ID, r -> {
            long n = 1 + r.nextInt(5000);
            long want = PoliteStacks.politeness(n);
            return new Puzzle("polite", "In how many runs of 2+ consecutive bar counts can " + n + " bars stack?",
                Long.toString(want), a -> a.matches("\\d{1,18}")
                    && PoliteStacks.grade(n, Long.parseLong(a)) == PoliteStacks.Grade.TURNED);
        }, PoliteStacks.forgemasterLine(PoliteStacks.Grade.TURNED),
            PoliteStacks.forgemasterLine(PoliteStacks.Grade.SLIPPED)));
        Map<String, Game> m = new LinkedHashMap<>();
        for (Game x : g) {
            if (m.put(x.id(), x) != null) {
                throw new IllegalStateException("duplicate game id " + x.id());
            }
        }
        return Collections.unmodifiableMap(m);
    }

    /** All cabinet games in menu order. */
    public static List<Game> registry() {
        return List.copyOf(REGISTRY.values());
    }

    /** Game by id. */
    public static Game game(String id) {
        Game g = REGISTRY.get(id);
        if (g == null) {
            throw new IllegalArgumentException("no such cabinet game: " + id);
        }
        return g;
    }

    /** Numbered menu lines, "1. Carmichael Cycle [carmichael]". */
    public static List<String> menu() {
        List<String> out = new ArrayList<>();
        int i = 1;
        for (Game g : REGISTRY.values()) {
            out.add(i++ + ". " + g.title() + " [" + g.id() + "]");
        }
        return out;
    }

    /** One player's play loop on the cabinet. */
    public static final class Session {
        private final Random rng;
        private Puzzle current;
        private int score;
        private int streak;
        private int best;
        private int played;
        private int solved;

        /** Start a seeded session. */
        public Session(long seed) {
            this.rng = new Random(seed);
        }

        /** Deal the next puzzle from game id, replacing any open puzzle. */
        public Puzzle next(String id) {
            current = game(id).deal(rng);
            return current;
        }

        /** Deal from menu slot 1..size. */
        public Puzzle pick(int slot) {
            List<Game> all = registry();
            if (slot < 1 || slot > all.size()) {
                throw new IllegalArgumentException("no menu slot " + slot);
            }
            return next(all.get(slot - 1).id());
        }

        /** Submit an answer for the open puzzle. */
        public Result submit(String answer) {
            if (current == null) {
                throw new IllegalStateException("no open puzzle");
            }
            Puzzle p = current;
            current = null;
            boolean ok = p.check(answer);
            played++;
            int pts = 0;
            if (ok) {
                solved++;
                streak++;
                best = Math.max(best, streak);
                pts = BASE_POINTS * Math.min(streak, MAX_STREAK_BONUS);
                score += pts;
            } else {
                streak = 0;
            }
            return new Result(p.gameId(), ok, p.reference(), game(p.gameId()).line(ok), pts, streak, score);
        }

        /** True when a puzzle is waiting for an answer. */
        public boolean hasOpenPuzzle() {
            return current != null;
        }

        /** Current score. */
        public int score() {
            return score;
        }

        /** Summary line for the quest hook. */
        public String summary() {
            return QUEST_ID + ": solved " + solved + "/" + played + ", score " + score + ", best streak " + best;
        }
    }
}
