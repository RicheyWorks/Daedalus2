// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.HashSet;
import java.util.List;
import java.util.Random;
import java.util.Set;
import org.junit.jupiter.api.Test;

class ForgeCabinetTest {

    private static String perturb(String ref) {
        if ("prime".equals(ref)) {
            return "composite";
        }
        if ("composite".equals(ref)) {
            return "prime";
        }
        if ("smith".equals(ref)) {
            return "plain";
        }
        if ("plain".equals(ref)) {
            return "smith";
        }
        if ("practical".equals(ref)) {
            return "short";
        }
        if ("short".equals(ref)) {
            return "practical";
        }
        if ("record".equals(ref)) {
            return "common";
        }
        if ("common".equals(ref)) {
            return "record";
        }
        if ("achilles".equals(ref)) {
            return "brittle";
        }
        if ("brittle".equals(ref)) {
            return "achilles";
        }
        if ("weird".equals(ref)) {
            return "tame";
        }
        if ("tame".equals(ref)) {
            return "weird";
        }
        if ("untouched".equals(ref)) {
            return "touched";
        }
        if ("touched".equals(ref)) {
            return "untouched";
        }
        if ("ludic".equals(ref)) {
            return "culled";
        }
        if ("culled".equals(ref)) {
            return "ludic";
        }
        if ("keith".equals(ref)) {
            return "cold";
        }
        if ("cold".equals(ref)) {
            return "keith";
        }
        if ("self".equals(ref)) {
            return "stamped";
        }
        if ("stamped".equals(ref)) {
            return "self";
        }
        if ("triad".equals(ref)) {
            return "mixed";
        }
        if ("mixed".equals(ref)) {
            return "triad";
        }
        if ("pernicious".equals(ref)) {
            return "plainpin";
        }
        if ("plainpin".equals(ref)) {
            return "pernicious";
        }
        if ("duffin".equals(ref)) {
            return "commondie";
        }
        if ("commondie".equals(ref)) {
            return "duffin";
        }
        if (ref.contains(",")) {
            String[] p = ref.split(",");
            return (Long.parseLong(p[0]) + 1) + "," + p[1];
        }
        if (ref.contains("/")) {
            String[] p = ref.split("/");
            return (Long.parseLong(p[0]) + 1) + "/" + p[1];
        }
        return new BigInteger(ref).add(BigInteger.ONE).toString();
    }

    @Test
    void registryListsOurForgeGames() {
        List<ForgeCabinet.Game> games = ForgeCabinet.registry();
        assertThat(games).hasSize(30);
        Set<String> ids = new HashSet<>();
        for (ForgeCabinet.Game g : games) {
            assertThat(ids.add(g.id())).isTrue();
            assertThat(g.toolQuest()).startsWith("q_");
            assertThat(g.line(true)).startsWith("Forgemaster:");
            assertThat(g.line(false)).startsWith("Forgemaster:").isNotEqualTo(g.line(true));
            assertThat(ForgeCabinet.game(g.id())).isSameAs(g);
        }
        List<String> menu = ForgeCabinet.menu();
        assertThat(menu).hasSize(30);
        assertThat(menu.get(0)).isEqualTo("1. Carmichael Cycle [carmichael]");
        assertThat(menu.get(13)).isEqualTo("14. Automorph Anvil [automorph]");
        assertThat(menu.get(14)).isEqualTo("15. Smith Stamps [smith]");
        assertThat(menu.get(15)).isEqualTo("16. Practical Weights [practical]");
        assertThat(ForgeCabinet.game("smith").toolQuest()).isEqualTo(SmithStamps.QUEST_ID);
        assertThat(ForgeCabinet.game("practical").toolQuest()).isEqualTo(PracticalWeights.QUEST_ID);
        assertThat(menu.get(16)).isEqualTo("17. Record Ingots [record]");
        assertThat(ForgeCabinet.game("record").toolQuest()).isEqualTo(RecordIngots.QUEST_ID);
        assertThat(menu.get(17)).isEqualTo("18. Achilles Rivets [achilles]");
        assertThat(ForgeCabinet.game("achilles").toolQuest()).isEqualTo(AchillesRivets.QUEST_ID);
        assertThat(menu.get(18)).isEqualTo("19. Weird Hoards [weird]");
        assertThat(ForgeCabinet.game("weird").toolQuest()).isEqualTo(WeirdHoards.QUEST_ID);
        assertThat(menu.get(19)).isEqualTo("20. Untouched Brands [untouched]");
        assertThat(ForgeCabinet.game("untouched").toolQuest()).isEqualTo(UntouchedBrands.QUEST_ID);
        assertThat(menu.get(20)).isEqualTo("21. Ludic Lots [ludic]");
        assertThat(ForgeCabinet.game("ludic").toolQuest()).isEqualTo(LudicLots.QUEST_ID);
        assertThat(menu.get(21)).isEqualTo("22. Keith Kindling [keith]");
        assertThat(ForgeCabinet.game("keith").toolQuest()).isEqualTo(KeithKindling.QUEST_ID);
        assertThat(menu.get(22)).isEqualTo("23. Self Forged [self]");
        assertThat(ForgeCabinet.game("self").toolQuest()).isEqualTo(SelfForged.QUEST_ID);
        assertThat(menu.get(23)).isEqualTo("24. Triad Alloys [triad]");
        assertThat(ForgeCabinet.game("triad").toolQuest()).isEqualTo(TriadAlloys.QUEST_ID);
        assertThat(menu.get(24)).isEqualTo("25. Pernicious Pins [pernicious]");
        assertThat(ForgeCabinet.game("pernicious").toolQuest()).isEqualTo(PerniciousPins.QUEST_ID);
        assertThat(menu.get(25)).isEqualTo("26. Polite Stacks [polite]");
        assertThat(ForgeCabinet.game("polite").toolQuest()).isEqualTo(PoliteStacks.QUEST_ID);
        assertThat(menu.get(26)).isEqualTo("27. Duffin Dies [duffin]");
        assertThat(ForgeCabinet.game("duffin").toolQuest()).isEqualTo(DuffinDies.QUEST_ID);
        assertThat(menu.get(27)).isEqualTo("28. Primorial Pyres [primorial]");
        assertThat(ForgeCabinet.game("primorial").toolQuest()).isEqualTo(PrimorialPyres.QUEST_ID);
        assertThat(menu.get(28)).isEqualTo("29. Cullen Crucibles [cullen]");
        assertThat(ForgeCabinet.game("cullen").toolQuest()).isEqualTo(CullenCrucibles.QUEST_ID);
        assertThat(menu.get(29)).isEqualTo("30. Proth Plates [proth]");
        assertThat(ForgeCabinet.game("proth").toolQuest()).isEqualTo(ProthPlates.QUEST_ID);
        assertThat(ForgeCabinet.game("lucas").toolQuest()).isEqualTo(LucasLattice.QUEST_ID);
        assertThatThrownBy(() -> ForgeCabinet.game("nope")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ForgeCabinet.registry().clear()).isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void referenceAnswersPassAndPerturbedFailForEveryGame() {
        Random r = new Random(465);
        for (ForgeCabinet.Game g : ForgeCabinet.registry()) {
            for (int t = 0; t < 150; t++) {
                ForgeCabinet.Puzzle p = g.deal(r);
                assertThat(p.gameId()).isEqualTo(g.id());
                assertThat(p.prompt()).isNotBlank();
                assertThat(p.check(p.reference())).as("%s %s", g.id(), p.prompt()).isTrue();
                assertThat(p.check(perturb(p.reference()))).as("%s perturbed %s", g.id(), p.prompt()).isFalse();
            }
        }
    }

    @Test
    void malformedAnswersFailQuietly() {
        Random r = new Random(4650);
        String[] bad = {null, "", "   ", "abc", "1,2,3", "1/0", "1/2/3", "99999999999999999999999", "--1", "maybe"};
        for (ForgeCabinet.Game g : ForgeCabinet.registry()) {
            ForgeCabinet.Puzzle p = g.deal(r);
            for (String b : bad) {
                assertThat(p.check(b)).as("%s <%s>", g.id(), b).isFalse();
            }
        }
    }

    @Test
    void equivalentAnswersAreAccepted() {
        Random r = new Random(4651);
        for (int t = 0; t < 100; t++) {
            ForgeCabinet.Puzzle m = ForgeCabinet.game("mersenne").deal(r);
            assertThat(m.check("  " + m.reference().toUpperCase(java.util.Locale.ROOT) + " ")).isTrue();
            ForgeCabinet.Puzzle a = ForgeCabinet.game("automorph").deal(r);
            assertThat(a.check("000" + a.reference())).isTrue();
            ForgeCabinet.Puzzle g = ForgeCabinet.game("gaussian").deal(r);
            String[] s = g.reference().split(",");
            assertThat(g.check(s[1] + " , " + s[0])).isTrue();
            assertThat(g.check("-" + s[0] + "," + s[1])).isTrue();
            ForgeCabinet.Puzzle d = ForgeCabinet.game("dedekind").deal(r);
            String[] q = d.reference().split("/");
            assertThat(d.check((2 * Long.parseLong(q[0])) + "/" + (2 * Long.parseLong(q[1])))).isTrue();
            ForgeCabinet.Puzzle f = ForgeCabinet.game("fermat").deal(r);
            String[] fs = f.reference().split(",");
            assertThat(f.check(fs[1] + "," + fs[0])).isTrue();
        }
    }

    @Test
    void sessionLoopScoresStreaksAndGuards() {
        ForgeCabinet.Session s = new ForgeCabinet.Session(7);
        assertThat(s.hasOpenPuzzle()).isFalse();
        assertThatThrownBy(() -> s.submit("1")).isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(() -> s.pick(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> s.pick(31)).isInstanceOf(IllegalArgumentException.class);
        int expected = 0;
        for (int i = 1; i <= 7; i++) {
            ForgeCabinet.Puzzle p = s.pick(i);
            assertThat(s.hasOpenPuzzle()).isTrue();
            ForgeCabinet.Result res = s.submit(p.reference());
            expected += ForgeCabinet.BASE_POINTS * Math.min(i, ForgeCabinet.MAX_STREAK_BONUS);
            assertThat(res.correct()).isTrue();
            assertThat(res.streak()).isEqualTo(i);
            assertThat(res.score()).isEqualTo(expected);
            assertThat(res.line()).isEqualTo(ForgeCabinet.game(p.gameId()).line(true));
        }
        ForgeCabinet.Puzzle p = s.next("harshad");
        ForgeCabinet.Result miss = s.submit(perturb(p.reference()));
        assertThat(miss.correct()).isFalse();
        assertThat(miss.points()).isZero();
        assertThat(miss.streak()).isZero();
        assertThat(miss.reference()).isEqualTo(p.reference());
        assertThat(miss.score()).isEqualTo(expected);
        assertThatThrownBy(() -> s.submit("1")).isInstanceOf(IllegalStateException.class);
        assertThat(s.summary()).isEqualTo("q_forge_cabinet: solved 7/8, score " + expected + ", best streak 7");
    }

    @Test
    void seededSessionsAreDeterministicAndLongRunsScoreConsistently() {
        ForgeCabinet.Session a = new ForgeCabinet.Session(99);
        ForgeCabinet.Session b = new ForgeCabinet.Session(99);
        Random pick = new Random(1);
        int score = 0;
        int streak = 0;
        for (int t = 0; t < 1500; t++) {
            int slot = 1 + pick.nextInt(30);
            ForgeCabinet.Puzzle pa = a.pick(slot);
            ForgeCabinet.Puzzle pb = b.pick(slot);
            assertThat(pa.prompt()).isEqualTo(pb.prompt());
            boolean right = pick.nextInt(4) != 0;
            ForgeCabinet.Result ra = a.submit(right ? pa.reference() : perturb(pa.reference()));
            b.submit(pb.reference());
            if (right) {
                streak++;
                score += ForgeCabinet.BASE_POINTS * Math.min(streak, ForgeCabinet.MAX_STREAK_BONUS);
            } else {
                streak = 0;
            }
            assertThat(ra.correct()).isEqualTo(right);
            assertThat(ra.score()).isEqualTo(score);
        }
        assertThat(a.score()).isEqualTo(score);
        assertThat(b.score()).isEqualTo(10 + 20 + 30 + 40 + 50 * 1496);
    }
}
