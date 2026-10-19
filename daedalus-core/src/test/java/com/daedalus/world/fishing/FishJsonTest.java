// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class FishJsonTest {

    @Test
    void parsesEveryJsonShape() {
        Object v = FishJson.parse(" {\"a\": [1, -2.5e1, true, false, null, {}, []], \"s\": \"q\\\"\\\\\\/\\n\\t\\r\\b\\f\\u0041\"} ");
        Map<?, ?> m = (Map<?, ?>) v;
        assertThat(((List<?>) m.get("a")).toArray()).containsExactly(1.0, -25.0, true, false, null, Map.of(), List.of());
        assertThat(m.get("s")).isEqualTo("q\"\\/\n\t\r\b\fA");
    }

    @Test
    void rejectsBrokenJson() {
        for (String bad : new String[] {"", "{", "[1,", "{\"a\" 1}", "{\"a\":1} x", "tru", "@", "\"\\x\"", "\"\\u12\"",
            "\"\\uZZZZ\"", "1e", "[1 2]"}) {
            assertThatThrownBy(() -> FishJson.parse(bad)).as(bad).isInstanceOf(IllegalArgumentException.class)
                    .hasMessageStartingWith("fish json");
        }
    }

    @Test
    void readsATableAndItsOptionalFields() {
        FishTable t = FishTable.fromJson("{\"fish\":[{\"name\":\"a\",\"rarity\":\"rare\",\"weight\":2,\"window_s\":0.5,"
                + "\"seasons\":[\"winter\"],\"spots\":[\"pier\"],\"dusk_only\":true}]}");
        FishSpecies a = t.require("a");
        assertThat(t.realm()).isEqualTo("unknown");
        assertThat(a.price()).isZero();
        assertThat(a.nightWeight()).isZero();
        assertThat(a.seasons()).containsExactly("winter");
        assertThat(a.spots()).containsExactly("pier");
        assertThat(a.duskOnly()).isTrue();
    }

    @Test
    void tableErrorsNameTheProblem() {
        assertThatThrownBy(() -> FishTable.fromJson(null)).hasMessageContaining("no text");
        assertThatThrownBy(() -> FishTable.fromJson("[]")).hasMessageContaining("document must be an object");
        assertThatThrownBy(() -> FishTable.fromJson("{}")).hasMessageContaining("'fish' must be a list");
        assertThatThrownBy(() -> FishTable.fromJson("{\"fish\":[1]}")).hasMessageContaining("fish entry");
        assertThatThrownBy(() -> FishTable.fromJson("{\"fish\":[{\"rarity\":\"RARE\"}]}")).hasMessageContaining("'name'");
        assertThatThrownBy(() -> FishTable.fromJson("{\"fish\":[{\"name\":3}]}")).hasMessageContaining("must be text");
        assertThatThrownBy(() -> FishTable.fromJson("{\"fish\":[{\"name\":\"a\",\"rarity\":\"RARE\",\"window_s\":1}]}"))
                .hasMessageContaining("no 'weight'");
        assertThatThrownBy(() -> FishTable.fromJson("{\"fish\":[{\"name\":\"a\",\"rarity\":\"RARE\",\"weight\":\"x\"}]}"))
                .hasMessageContaining("must be a number");
        assertThatThrownBy(() -> FishTable.fromJson(
                "{\"fish\":[{\"name\":\"a\",\"rarity\":\"RARE\",\"weight\":1,\"window_s\":1,\"spots\":[1]}]}"))
                .hasMessageContaining("must hold text");
    }
}
