// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.balance;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.odds.OddsRng;
import java.util.List;
import org.junit.jupiter.api.Test;

class BalanceTunerTest {

    /** Toy game: one knob k in 0..20, win probability k / 20, shipped easy=20, normal=10, hard missing. */
    private static TunableGame toy() {
        return new TunableGame() {
            @Override
            public String id() {
                return "toy";
            }

            @Override
            public List<String> difficulties() {
                return List.of("easy", "normal", "hard");
            }

            @Override
            public List<Knob> knobs() {
                return List.of(new Knob("k", 0, 20, 1));
            }

            @Override
            public int[] shipped(String d) {
                return "easy".equals(d) ? new int[] {20} : "normal".equals(d) ? new int[] {10} : null;
            }

            @Override
            public SessionOutcome play(int[] knobs, OddsRng rng) {
                return new SessionOutcome(rng.chance(knobs[0] / 20.0), knobs[0]);
            }
        };
    }

    /** Narrow, disjoint bands with one known answer each: easy 16 (80%), normal 10 (50%), hard 4 (20%). */
    private static BalanceCheck narrow() {
        return new BalanceCheck(new BalanceBand(0, 1)).band("easy", new BalanceBand(0.76, 0.84))
                .band("normal", new BalanceBand(0.46, 0.54)).band("hard", new BalanceBand(0.16, 0.24));
    }

    @Test
    void findsTheKnownInBandValuesOnAToyGame() {
        List<Suggestion> s = new BalanceTuner(narrow(), 3000, 3000, 1_000_000).tune(toy(), 7L);
        assertThat(s).extracting(Suggestion::difficulty).containsExactly("easy", "normal", "hard");
        assertThat(s).allMatch(Suggestion::found);
        assertThat(s.get(0).suggested()).containsExactly(16);
        assertThat(s.get(1).suggested()).containsExactly(10);
        assertThat(s.get(2).suggested()).containsExactly(4);
        assertThat(s.get(2).shipped()).isNull();
        for (Suggestion x : s) {
            BalanceBand b = narrow().bandFor(x.difficulty());
            assertThat(x.confirm().low()).isGreaterThanOrEqualTo(b.floor());
            assertThat(x.confirm().high()).isLessThanOrEqualTo(b.ceiling());
        }
    }

    @Test
    void sameSeedGivesTheSameSuggestions() {
        BalanceTuner t = new BalanceTuner(new BalanceCheck(), 200, 800, 2_000_000);
        assertThat(t.tune(TunerReport.cairnwell(), 11L)).usingRecursiveFieldByFieldElementComparator()
                .isEqualTo(t.tune(TunerReport.cairnwell(), 11L));
        List<Suggestion> a = t.tune(toy(), 3L);
        List<Suggestion> b = t.tune(toy(), 3L);
        for (int i = 0; i < a.size(); i++) {
            assertThat(a.get(i).toString()).isEqualTo(b.get(i).toString());
        }
    }

    @Test
    void monotonicCheckNeedsStrictlySeparatedIntervals() {
        ModeResult hi = new ModeResult("g", "easy", 100, 90, 0, new double[] {0.8, 0.95});
        ModeResult mid = new ModeResult("g", "normal", 100, 50, 0, new double[] {0.4, 0.6});
        ModeResult lo = new ModeResult("g", "hard", 100, 20, 0, new double[] {0.1, 0.3});
        ModeResult overlap = new ModeResult("g", "hard", 100, 55, 0, new double[] {0.45, 0.65});
        assertThat(BalanceTuner.monotonic(List.of(hi, mid, lo))).isTrue();
        assertThat(BalanceTuner.monotonic(List.of(hi, mid, overlap))).isFalse();
        assertThat(BalanceTuner.monotonic(List.of(mid, hi))).isFalse();
    }

    @Test
    void publishedSuggestionsAreInBandAndMonotonic() {
        List<Suggestion> all = TunerReport.runAll(TunerReport.SEED);
        BalanceCheck check = new BalanceCheck();
        for (String game : List.of("shardring", "cairnwell")) {
            List<Suggestion> g = all.stream().filter(s -> s.game().equals(game)).toList();
            assertThat(g).hasSize(3).allMatch(Suggestion::found);
            for (Suggestion s : g) {
                BalanceBand b = check.bandFor(s.difficulty());
                assertThat(s.confirm().low()).isGreaterThanOrEqualTo(b.floor());
                assertThat(s.confirm().high()).isLessThanOrEqualTo(b.ceiling());
            }
            assertThat(BalanceTuner.monotonic(g.stream().map(Suggestion::confirm).toList())).isTrue();
        }
        Suggestion hard = all.get(5);
        assertThat(hard.game()).isEqualTo("cairnwell");
        assertThat(hard.shipped()).containsExactly(6, 5, 8);
    }

    @Test
    void runtimeIsBoundedBySessionCap() {
        assertThatThrownBy(() -> new BalanceTuner(new BalanceCheck(), 1000, 1000, 10_000).tune(TunerReport.shardring(),
                1L)).isInstanceOf(IllegalArgumentException.class).hasMessageContaining("exceeds cap");
        long start = System.nanoTime();
        TunerReport.runAll(TunerReport.SEED);
        assertThat((System.nanoTime() - start) / 1e9).isLessThan(60.0);
    }

    @Test
    void gridAndKnobsAreValidated() {
        assertThat(BalanceTuner.grid(List.of(new Knob("a", 1, 3, 1), new Knob("b", 0, 10, 5)))).hasSize(9);
        assertThat(new Knob("x", 6, 28, 2).size()).isEqualTo(12);
        assertThatThrownBy(() -> new Knob("x", 5, 4, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new BalanceTuner(new BalanceCheck(), 0, 1, 1))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
