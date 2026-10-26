// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import org.junit.jupiter.api.Test;

class DawnChorusCensusTest {
    @Test void soundscapeCensusSolvesEveryDawn() {
        for (long s = 0; s < 300; s++) {
            DawnChorusCensus d = DawnChorusCensus.seeded(s);
            List<DawnChorusCensus.Call> sc = d.soundscape();
            for (int i = 1; i < sc.size(); i++) {
                assertThat(sc.get(i).onsetMs()).isGreaterThanOrEqualTo(sc.get(i - 1).onsetMs());
            }
            assertThat(sc).allMatch(c -> c.onsetMs() >= 0 && c.onsetMs() < DawnChorusCensus.LISTEN_MS);
            List<Integer> census = DawnChorusCensus.census(sc);
            assertThat(census.stream().filter(n -> n == 0).count()).isEqualTo(1);
            int max = census.stream().mapToInt(Integer::intValue).max().orElseThrow();
            assertThat(census.stream().filter(n -> n == max).count()).isEqualTo(1);
            List<String> ans = d.solution();
            assertThat(d.judge(ans.get(0), ans.get(1)).correct()).as("seed %d", s).isTrue();
            assertThat(d.seed()).isEqualTo(s);
        }
    }

    @Test void mostCallsIsNotMostBirds() {
        // a cricket calls 30 times a minute, an owl 6: abundance is calls x period
        List<DawnChorusCensus.Call> heard = new java.util.ArrayList<>();
        for (int t = 0; t < 60_000; t += 2000) {
            heard.add(new DawnChorusCensus.Call(t, 329.628));
        }
        for (int k = 0; k < 2; k++) {
            for (int t = k * 100; t < 60_000; t += 10_000) {
                heard.add(new DawnChorusCensus.Call(t, 195.998));
            }
        }
        List<Integer> c = DawnChorusCensus.census(heard);
        assertThat(c.get(4)).isEqualTo(1);
        assertThat(c.get(2)).isEqualTo(2);
    }

    @Test void judgeSplitsBothAnswers() {
        DawnChorusCensus d = DawnChorusCensus.seeded(6);
        DawnChorusCensus.Verdict truth = d.judge("x", "y");
        assertThat(truth.correct()).isFalse();
        assertThat(d.judge(truth.loudest(), "y").rightLoudest()).isTrue();
        assertThat(d.judge(truth.loudest(), "y").rightMissing()).isFalse();
        assertThat(d.judge("x", truth.missing()).rightMissing()).isTrue();
    }
}