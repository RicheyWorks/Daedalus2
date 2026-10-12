// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox.radio;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class RadioServiceTest {

    @Test
    void searchesGoMostLocalFirstAndPortComputerPetsParams() {
        List<String> s = RadioService.searches(RadioArea.parse("Seattle, Washington, US", 47.6062, -122.3321, null));
        assertThat(s.get(0)).contains("geo_lat=47.6062").contains("geo_long=-122.3321").contains("geo_distance=120000");
        assertThat(s.get(1)).contains("city=Seattle").contains("state=Washington").contains("countrycode=US");
        assertThat(s).allMatch(p -> p.startsWith("/json/stations/search?limit=60&hidebroken=true&order=clickcount&reverse=true"));
        assertThat(s).hasSizeLessThanOrEqualTo(4);
        assertThat(RadioService.searches(RadioArea.NONE)).containsExactly("/json/stations/search?limit=60&hidebroken=true&order=clickcount&reverse=true");
        assertThat(RadioService.searches(RadioArea.parse("", null, null, "de"))).containsExactly(
                "/json/stations/search?limit=60&hidebroken=true&order=clickcount&reverse=true&countrycode=DE");
    }

    @Test
    void lineupRanksCachesAndOnlyRelaysListedStations() {
        List<String> asked = new ArrayList<>();
        RadioDirectory dir = path -> {
            asked.add(path);
            return List.of(RadioRankingTest.BERLIN, RadioRankingTest.KEXP, RadioRankingTest.KSUH_AM);
        };
        AtomicLong now = new AtomicLong();
        RadioService radio = new RadioService(dir, now::get);
        RadioService.Lineup l = radio.lineup(RadioRankingTest.SEATTLE);
        assertThat(l.stations().get(0).station().id()).isEqualTo("kexp");
        assertThat(l.note()).isEmpty();
        int calls = asked.size();
        radio.lineup(RadioRankingTest.SEATTLE);
        assertThat(asked).hasSize(calls);                       // cached
        assertThat(radio.streamOf("kexp")).contains("https://s/kexp");
        assertThat(radio.streamOf("http://evil.example/")).isEmpty();
        assertThat(radio.streamOf(null)).isEmpty();
    }

    @Test
    void partialOutagesStillAnswerAndATotalOneFails() {
        RadioDirectory flaky = path -> {
            if (path.contains("geo_lat")) throw new IllegalStateException("down");
            return List.of(RadioRankingTest.KIRO_FM);
        };
        assertThat(new RadioService(flaky, () -> 0).lineup(RadioRankingTest.SEATTLE).stations()).hasSize(1);
        RadioDirectory down = path -> { throw new IllegalStateException("down"); };
        assertThatThrownBy(() -> new RadioService(down, () -> 0).lineup(RadioRankingTest.SEATTLE)).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void notesExplainNoLocationAndNoLocalFm() {
        RadioService r = new RadioService(path -> List.of(RadioRankingTest.BERLIN), () -> 0);
        assertThat(r.lineup(RadioArea.NONE).note()).contains("No location");
        assertThat(r.lineup(RadioRankingTest.SEATTLE).note()).contains("No local FM");
        assertThat(new RadioService(path -> List.of(), () -> 0).lineup(RadioRankingTest.SEATTLE).note()).contains("No stations");
    }

    @Test
    void parsesDirectoryRowsSafelyLikeComputerPets() throws Exception {
        String json = """
            [{"stationuuid":"a","name":"  KEXP  ","url_resolved":"https://live.kexp.org/kexp160.aac","state":"Washington","countrycode":"US","geo_lat":47.6,"geo_long":-122.3},
             {"stationuuid":"b","name":"Bad","url":"javascript:alert(1)"},
             {"stationuuid":"c","name":"Creds","url":"http://u:p@host/stream"},
             {"stationuuid":"d","name":"","url":"https://x/y"},
             {"stationuuid":"e","name":"NoGeo","url":"http://x/y","geo_lat":null}]""";
        List<RadioStation> s = RadioStation.parse(new ObjectMapper().readTree(json));
        assertThat(s).extracting(RadioStation::id).containsExactly("a", "e");
        assertThat(s.get(0).name()).isEqualTo("KEXP");
        assertThat(s.get(1).lat()).isNull();
        assertThat(s.get(1).https()).isFalse();
    }

    @Test
    void areaParsingPortsComputerPets() {
        RadioArea a = RadioArea.parse("Leeds, West Yorkshire, United Kingdom", null, null, null);
        assertThat(a.city()).isEqualTo("Leeds");
        assertThat(a.state()).isEqualTo("West Yorkshire");
        assertThat(a.countrycode()).isEqualTo("GB");
        assertThat(RadioArea.parse("Paris", null, null, "fr").countrycode()).isEqualTo("FR");
        assertThat(RadioArea.parse(null, 200.0, 5.0, null).hasCoords()).isFalse();
        assertThat(RadioArea.parse(null, null, null, null).isEmpty()).isTrue();
    }
}
