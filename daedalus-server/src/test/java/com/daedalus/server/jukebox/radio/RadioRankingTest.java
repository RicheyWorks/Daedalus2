// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox.radio;

import org.junit.jupiter.api.RepeatedTest;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;

import static com.daedalus.server.jukebox.radio.RadioRanking.Tier.ELSEWHERE;
import static com.daedalus.server.jukebox.radio.RadioRanking.Tier.LOCAL;
import static com.daedalus.server.jukebox.radio.RadioRanking.Tier.LOCAL_FM;
import static org.assertj.core.api.Assertions.assertThat;

class RadioRankingTest {

    static final RadioArea SEATTLE = RadioArea.parse("Seattle, Washington, US", 47.6062, -122.3321, null);

    static RadioStation st(String id, String name, String state, String cc, Double lat, Double lon) {
        return new RadioStation(id, name, "https://s/" + id, "", state, state, "", cc, lat, lon);
    }

    static final RadioStation KEXP = st("kexp", "KEXP 90.3 FM", "Washington", "US", 47.62, -122.35);
    static final RadioStation KIRO_FM = st("kiro", "KIRO -FM", "Washington", "US", 47.59, -122.33);
    static final RadioStation TACOMA_FM = st("tac", "Space 101.1 FM", "Washington", "US", 47.24, -122.46);
    static final RadioStation KSUH_AM = st("ksuh", "Radio Hankook KSUH 1450 AM", "Washington", "US", 47.31, -122.33);
    static final RadioStation KUOW = st("kuow", "KUOW", "WA", "US", 47.60, -122.33);
    static final RadioStation PORTLAND_FM = st("pdx", "KINK 101.9 FM", "Oregon", "US", 45.52, -122.68);
    static final RadioStation BERLIN = st("ber", "Radio Eins", "Berlin", "DE", 52.52, 13.40);
    static final RadioStation NO_GEO = st("nogeo", "Hits 24/7", "", "US", null, null);

    static List<RadioStation> all() {
        return List.of(BERLIN, KUOW, PORTLAND_FM, KSUH_AM, NO_GEO, TACOMA_FM, KIRO_FM, KEXP);
    }

    @Test
    void localFmComesFirstNearestFirstThenOtherLocalThenTheRest() {
        List<RadioRanking.Ranked> r = RadioRanking.rank(all(), SEATTLE);
        assertThat(r).extracting(x -> x.station().id())
                // local FM by distance (1.4, 2, 41 km); other local by distance (KUOW 0.3 km, AM 32 km); the rest by score
                .containsExactly("kiro", "kexp", "tac", "kuow", "ksuh", "pdx", "nogeo", "ber");
        assertThat(r).extracting(RadioRanking.Ranked::tier)
                .containsExactly(LOCAL_FM, LOCAL_FM, LOCAL_FM, LOCAL, LOCAL, ELSEWHERE, ELSEWHERE, ELSEWHERE);
    }

    /** The guarantee, whatever order the directory answers in: no non-local-FM station ever precedes a local FM one. */
    @RepeatedTest(25)
    void theGuaranteeHoldsForAnyInputOrder() {
        List<RadioStation> in = new ArrayList<>(all());
        Collections.shuffle(in, new Random());
        List<RadioRanking.Ranked> r = RadioRanking.rank(in, SEATTLE);
        int lastFm = -1, firstOther = Integer.MAX_VALUE;
        for (int i = 0; i < r.size(); i++) {
            if (r.get(i).tier() == LOCAL_FM) lastFm = i;
            else firstOther = Math.min(firstOther, i);
        }
        assertThat(lastFm).isLessThan(firstOther);
        assertThat(r).isSortedAccordingTo((a, b) -> a.tier().compareTo(b.tier()));
    }

    @Test
    void withoutCoordinatesATypedCityDecidesWhatIsLocal() {
        RadioArea typed = RadioArea.parse("Seattle, Washington, US", null, null, null);
        RadioStation cityFm = st("c", "Seattle's 98.9 FM", "Washington", "US", null, null);
        RadioStation cityAm = st("a", "Seattle 710 AM", "Washington", "US", null, null);
        List<RadioRanking.Ranked> r = RadioRanking.rank(List.of(BERLIN, cityAm, KUOW, cityFm), typed);
        assertThat(r).extracting(x -> x.station().id()).startsWith("c", "a");
        assertThat(r.get(0).tier()).isEqualTo(LOCAL_FM);
    }

    @Test
    void noLocationMeansNothingIsCalledLocal() {
        assertThat(RadioRanking.rank(all(), RadioArea.NONE)).extracting(RadioRanking.Ranked::tier).containsOnly(ELSEWHERE);
    }

    @Test
    void bandsAndDistanceAndMerge() {
        assertThat(KEXP.band()).isEqualTo(RadioStation.Band.FM);
        assertThat(KIRO_FM.band()).isEqualTo(RadioStation.Band.FM);
        assertThat(KSUH_AM.band()).isEqualTo(RadioStation.Band.AM);
        assertThat(st("x", "Hits 101.9", "", "", null, null).band()).isEqualTo(RadioStation.Band.FM);
        assertThat(st("x", "Hits 247", "", "", null, null).band()).isEqualTo(RadioStation.Band.OTHER);
        assertThat(st("x", "Fmusic", "", "", null, null).band()).isEqualTo(RadioStation.Band.OTHER);
        assertThat(RadioRanking.km(47.6062, -122.3321, 45.5152, -122.6784)).isBetween(230.0, 240.0);
        assertThat(RadioRanking.km(null, 1.0, 2.0, 3.0)).isNull();
        assertThat(RadioRanking.merge(List.of(List.of(KEXP, KUOW), List.of(KEXP, BERLIN)))).containsExactly(KEXP, KUOW, BERLIN);
    }
}
