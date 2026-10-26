// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.companion.TonicBrewer.Brew;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

class TonicEngineTest {
    private static TonicBook book;
    private static TonicBrewer brewer;

    @BeforeAll
    static void load() throws Exception {
        Path p = Path.of("..", "tools", "islands", "kennel-isle", "tonics.json");
        if (!Files.exists(p)) {
            p = Path.of("tools", "islands", "kennel-isle", "tonics.json");
        }
        book = TonicBook.load(p);
        brewer = new TonicBrewer(book);
    }

    @Test
    void loadsTheRealBook() {
        assertThat(book.recipes()).hasSize(100);
        assertThat(book.herbRoles()).hasSize(12);
        assertThat(book.maxHerbs()).isEqualTo(3);
        assertThat(book.decayDrinks()).isEqualTo(3);
        assertThat(book.recipes().stream().filter(r -> r.name() != null).map(r -> r.name()))
            .contains("Mend", "Bulwark", "Dash", "Fury", "Bond");
    }

    @Test
    void herbOrderDoesNotMatter() {
        assertThat(book.recipe(List.of("Furfern", "Pawmint", "Barkbalm")))
            .map(r -> r.id()).hasValue("tonic_barkbalm_pawmint_furfern");
        assertThat(book.recipe(List.of("Barkbalm", "Pawmint", "Furfern")))
            .map(r -> r.id()).hasValue("tonic_barkbalm_pawmint_furfern");
    }

    @Test
    void badHerbSetsFizzle() {
        assertThat(book.recipe(List.of())).isEmpty();
        assertThat(book.recipe(List.of("Barkbalm", "Barkbalm"))).isEmpty();
        assertThat(book.recipe(List.of("Nope"))).isEmpty();
        assertThat(book.recipe(List.of("Barkbalm", "Pawmint", "Furfern", "Dewclaw"))).isEmpty();
    }

    @Test
    void corsoDrinksAtFullStrengthAndSpotsBoostBursts() {
        Brew plain = brewer.brew(List.of("Barkbalm"), "None", TonicBrewer.CANE_CORSO, 1, false).orElseThrow();
        assertThat(plain.factor()).isEqualTo(1.0);
        assertThat(plain.mods().get(0).value()).isEqualTo(1.0);
        Brew spots = brewer.brew(List.of("Barkbalm"), "Spots", TonicBrewer.CANE_CORSO, 1, false).orElseThrow();
        assertThat(spots.factor()).isEqualTo(1.25);
        assertThat(spots.mods().get(0).value()).isEqualTo(1.25);
        Brew pack = brewer.brew(List.of("Barkbalm"), "None", TonicBrewer.PACK_MEMBER, 1, false).orElseThrow();
        assertThat(pack.mods().get(0).value()).isEqualTo(0.5);
    }

    @Test
    void mulModsScaleAroundOneAndCharmDoublesDuration() {
        Brew b = brewer.brew(List.of("Wagwort"), "None", TonicBrewer.PACK_MEMBER, 1, true).orElseThrow();
        assertThat(b.mods().get(0).op()).isEqualTo("mul");
        assertThat(b.mods().get(0).value()).isEqualTo(1.05);
        assertThat(b.durationSec()).isEqualTo(b.recipe().durationSec() * 2);
    }

    @Test
    void strengthIsBoundedForEveryRecipe() {
        for (TonicBook.Recipe r : book.recipes()) {
            for (String coat : List.of("Spots", "Stripes", "Labyrinth", "None", "Unknown")) {
                for (int stage = 1; stage <= 3; stage++) {
                    Brew b = brewer.scale(r, coat, TonicBrewer.CANE_CORSO, stage, true);
                    assertThat(b.factor()).isBetween(0.0, 2.0);
                    assertThat(b).isEqualTo(brewer.scale(r, coat, TonicBrewer.CANE_CORSO, stage, true));
                }
            }
        }
    }

    @Test
    void troughDecaysByDrinksAndTime() {
        TonicBook.Recipe r = book.recipe(List.of("Barkbalm")).orElseThrow();
        TroughBrew t = new TroughBrew(book, r, 0);
        assertThat(t.drink(10)).isTrue();
        assertThat(t.drink(20)).isTrue();
        assertThat(t.drink(30)).isTrue();
        assertThat(t.drink(40)).isFalse();
        TroughBrew flat = new TroughBrew(book, r, 0);
        assertThat(flat.drink(book.decayMinutes() * 60L)).isFalse();
        assertThat(flat.drinksLeft()).isEqualTo(3);
    }

    @Test
    void rejectsBadFiles() {
        assertThatThrownBy(() -> TonicBook.parse("{\"version\":2}")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> MiniJson.parse("{\"a\":1} x")).isInstanceOf(IllegalArgumentException.class);
        assertThat(MiniJson.parse("{\"a\":[1,\"b\\u0041\",true,null]}").toString()).isEqualTo("{a=[1.0, bA, true, null]}");
    }
}
