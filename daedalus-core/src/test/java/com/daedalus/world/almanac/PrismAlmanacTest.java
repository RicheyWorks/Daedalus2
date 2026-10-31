// SPDX-License-Identifier: MIT

package com.daedalus.world.almanac;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;

class PrismAlmanacTest {

    private static final Path CORE_TEST = Path.of("..", "engines", "unreal", "core-test");
    private static final String PARITY = "almanac_daily_parity.txt";
    private static final LocalDate FIRST = LocalDate.of(2026, 1, 1);
    private static final int DAYS = 365;

    private static Map<String, PrismAlmanac.Par> pars() throws IOException {
        return PrismAlmanac.parsFrom(Files.readAllLines(CORE_TEST.resolve("prism_fair_par_parity.txt"), StandardCharsets.UTF_8));
    }

    @Test
    void dayIsDealtLikeCpython() {
        // Pinned from python3: random.Random("prism-almanac:2026-10-30"), same draw order as PrismAlmanac.day.
        PrismAlmanac.Day d = PrismAlmanac.day(LocalDate.of(2026, 10, 30));
        assertThat(d.weather()).isEqualTo(PrismAlmanac.Weather.FOG);
        assertThat(d.picks()).containsExactly(new PrismAlmanac.Pick("facetlock", "easy", 590745773L),
                new PrismAlmanac.Pick("spiritkite", "easy", 675392333L), new PrismAlmanac.Pick("lumenpath", "normal", 707004768L));
    }

    @Test
    void everyDayDealsThreeDistinctCabinetsWithAPar() throws IOException {
        Map<String, PrismAlmanac.Par> pars = pars();
        assertThat(pars).hasSize(PrismAlmanac.GAMES.size() * PrismAlmanac.DIFFICULTIES.size());
        int[] dealt = new int[PrismAlmanac.GAMES.size()];
        Set<PrismAlmanac.Weather> weathers = new HashSet<>();
        for (int i = 0; i < DAYS; i++) {
            PrismAlmanac.Day d = PrismAlmanac.day(FIRST.plusDays(i));
            weathers.add(d.weather());
            assertThat(d.picks().stream().map(PrismAlmanac.Pick::game).distinct()).hasSize(PrismAlmanac.CABINETS_PER_DAY);
            for (PrismAlmanac.Posted posted : PrismAlmanac.post(d, pars)) {
                PrismAlmanac.Pick p = posted.pick();
                dealt[PrismAlmanac.GAMES.indexOf(p.game())]++;
                PrismAlmanac.Par par = posted.par();
                assertThat(PrismAlmanac.DIFFICULTIES.indexOf(posted.difficulty())).isLessThanOrEqualTo(PrismAlmanac.DIFFICULTIES.indexOf(p.difficulty()));
                assertThat(par.bronze()).isLessThanOrEqualTo(par.silver());
                assertThat(par.silver()).isLessThanOrEqualTo(par.gold());
                assertThat(p.seed()).isBetween(0L, 0xffffffffL);
            }
        }
        assertThat(weathers).hasSize(PrismAlmanac.Weather.values().length);
        for (int n : dealt) {
            // 1095 deals over 11 cabinets: about 100 each; every cabinet shows up regularly.
            assertThat(n).isBetween(60, 140);
        }
        assertThat(PrismAlmanac.day(FIRST)).isEqualTo(PrismAlmanac.day(FIRST));
    }

    @Test
    void uncalibratedDifficultyIsPlayedOneEasier() {
        Map<String, PrismAlmanac.Par> pars = Map.of("prismcairn/hard", new PrismAlmanac.Par(1, 0, 0), "prismcairn/normal",
                new PrismAlmanac.Par(1, 105, 105), "prismcairn/easy", new PrismAlmanac.Par(1, 105, 105));
        PrismAlmanac.Day d = new PrismAlmanac.Day(FIRST, PrismAlmanac.Weather.GALE,
                List.of(new PrismAlmanac.Pick("prismcairn", "hard", 7L)));
        assertThat(PrismAlmanac.post(d, pars)).containsExactly(new PrismAlmanac.Posted(d.picks().get(0), "normal",
                new PrismAlmanac.Par(1, 115, 115)));
        org.assertj.core.api.Assertions.assertThatThrownBy(() -> PrismAlmanac.post(new PrismAlmanac.Day(FIRST, PrismAlmanac.Weather.CALM,
                List.of(new PrismAlmanac.Pick("nowhere", "easy", 1L))), pars)).hasMessageContaining("no fair par");
    }

    @Test
    void streakAndRibbon() {
        long t = LocalDate.of(2026, 10, 30).toEpochDay();
        Set<Long> c = Set.of(t - 1, t - 2, t - 3, t - 5);
        assertThat(PrismAlmanac.streak(c, t)).isEqualTo(3);
        assertThat(PrismAlmanac.streak(Set.of(t, t - 1), t)).isEqualTo(2);
        assertThat(PrismAlmanac.streak(Set.of(t - 2), t)).isZero();
        assertThat(PrismAlmanac.ribbon(c, t)).isEqualTo(0b0111010);
        assertThat(PrismAlmanac.parFor(new PrismAlmanac.Par(1, 31, 42), PrismAlmanac.Weather.CLEAR_SKIES))
                .isEqualTo(new PrismAlmanac.Par(1, 27, 37));
    }

    static List<String> parityLines(Map<String, PrismAlmanac.Par> pars) {
        List<String> out = new ArrayList<>();
        for (int i = 0; i < DAYS; i++) {
            LocalDate date = FIRST.plusDays(i);
            PrismAlmanac.Day d = PrismAlmanac.day(date);
            StringBuilder b = new StringBuilder("date=" + date + " epoch=" + date.toEpochDay() + " weather=" + d.weather());
            for (PrismAlmanac.Posted posted : PrismAlmanac.post(d, pars)) {
                PrismAlmanac.Pick p = posted.pick();
                PrismAlmanac.Par par = posted.par();
                b.append(' ').append(p.game()).append('/').append(posted.difficulty()).append('/').append(p.seed()).append(":par=")
                        .append(par.bronze()).append(',').append(par.silver()).append(',').append(par.gold());
            }
            Set<Long> cleared = new HashSet<>();
            for (int k = 0; k < 10; k++) {
                if ((i + k * k) % 3 != 0) {
                    cleared.add(date.toEpochDay() - k);
                }
            }
            b.append(" streak=").append(PrismAlmanac.streak(cleared, date.toEpochDay())).append(" ribbon=")
                    .append(PrismAlmanac.ribbon(cleared, date.toEpochDay()));
            out.add(b.toString());
        }
        return out;
    }

    @Test
    void parityFileMatchesCpp() throws IOException {
        Path path = CORE_TEST.resolve(PARITY);
        List<String> actual = parityLines(pars());
        if (Boolean.getBoolean("almanac.parity.write")) {
            List<String> body = new ArrayList<>();
            body.add("# Prism Almanac Daily parity: written by PrismAlmanacTest.java, replayed by almanac_daily_core_test.cpp."
                    + " Days 2026-01-01..2026-12-31; pars from prism_fair_par_parity.txt; streak/ribbon over a fixed cleared pattern.");
            body.addAll(actual);
            Files.write(path, body, StandardCharsets.UTF_8);
        }
        assertThat(Files.readAllLines(path, StandardCharsets.UTF_8).stream().filter(l -> !l.startsWith("#") && !l.isBlank()).toList())
                .isEqualTo(actual);
    }
}
