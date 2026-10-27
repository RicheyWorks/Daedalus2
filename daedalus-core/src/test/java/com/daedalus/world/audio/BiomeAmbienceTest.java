// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;

/** Per-biome layer sets, state clamping, headroom and determinism of the ambience mixer. */
class BiomeAmbienceTest {
    private static final double[] LEVELS = {0, 0.25, 0.5, 1};

    private static Map<String, AmbienceLayer> mix(Biome b, double hour, double rain, double wind, double water) {
        return BiomeAmbience.mix(new AmbienceState(b, hour, rain, wind, water)).stream()
                .collect(Collectors.toMap(AmbienceLayer::id, l -> l));
    }

    @Test
    void everyStateGivesASortedBoundedDeterministicMix() {
        for (Biome b : Biome.values()) {
            for (int hour = 0; hour < 24; hour += 3) {
                for (double rain : LEVELS) {
                    for (double wind : LEVELS) {
                        for (double water : LEVELS) {
                            AmbienceState s = new AmbienceState(b, hour, rain, wind, water);
                            List<AmbienceLayer> m = BiomeAmbience.mix(s);
                            assertThat(BiomeAmbience.mix(s)).isEqualTo(m);
                            assertThat(m).isNotEmpty();
                            assertThat(m).extracting(AmbienceLayer::id).isSorted().doesNotHaveDuplicates();
                            double sum = 0;
                            for (AmbienceLayer l : m) {
                                assertThat(l.gain()).isGreaterThan(0).isLessThanOrEqualTo(BiomeAmbience.HEADROOM);
                                assertThat(l.density()).isBetween(0.0, 1.0);
                                assertThat(l.lowpassHz()).isBetween(3000.0, 18000.0);
                                sum += l.gain();
                            }
                            assertThat(sum).as(s.toString()).isLessThanOrEqualTo(BiomeAmbience.HEADROOM + 0.005);
                        }
                    }
                }
            }
        }
    }

    @Test
    void eachBiomeHasItsOwnSignatureLayers() {
        Map<Biome, List<String>> own = Map.of(
                Biome.FOREST, List.of("birds_day", "leaves", "owls_night"),
                Biome.GRASSLAND, List.of("insects_day", "crickets_night"),
                Biome.WETLAND, List.of("frogs", "reeds"),
                Biome.COAST, List.of("surf", "gulls"),
                Biome.DESERT, List.of("sand_hiss"),
                Biome.ALPINE, List.of("high_gust"),
                Biome.CAVE, List.of("drips", "room_tone"));
        assertThat(own.keySet()).containsExactlyInAnyOrder(Biome.values());
        List<String> all = own.values().stream().flatMap(List::stream).toList();
        for (Biome b : Biome.values()) {
            java.util.Set<String> seen = new java.util.HashSet<>();
            for (int hour = 0; hour < 24; hour++) {
                seen.addAll(mix(b, hour, 0.5, 0.5, 0.5).keySet());
            }
            assertThat(seen).as(b.toString()).containsAll(own.get(b));
            assertThat(seen).as(b + " borrows nothing").allMatch(id -> own.get(b).contains(id) || !all.contains(id));
            assertThat(seen).containsAll(List.of("wind", "rain", "water"));
        }
    }

    @Test
    void dayAndNightSwapTheRightCreatures() {
        assertThat(mix(Biome.FOREST, 13, 0, 0, 0)).containsKey("birds_day").doesNotContainKey("owls_night");
        assertThat(mix(Biome.FOREST, 1, 0, 0, 0)).containsKey("owls_night").doesNotContainKey("birds_day");
        assertThat(mix(Biome.GRASSLAND, 13, 0, 0, 0)).containsKey("insects_day").doesNotContainKey("crickets_night");
        assertThat(mix(Biome.GRASSLAND, 1, 0, 0, 0)).containsKey("crickets_night").doesNotContainKey("insects_day");
        assertThat(mix(Biome.COAST, 1, 0, 0, 0)).doesNotContainKey("gulls");
        assertThat(mix(Biome.WETLAND, 1, 0, 0, 0).get("frogs").gain())
                .isGreaterThan(mix(Biome.WETLAND, 13, 0, 0, 0).get("frogs").gain());
    }

    @Test
    void weatherDrivesTheRightLayers() {
        assertThat(mix(Biome.FOREST, 13, 0, 0, 0)).doesNotContainKeys("rain", "water", "leaves");
        assertThat(mix(Biome.DESERT, 13, 0, 0, 0)).doesNotContainKey("sand_hiss").containsKey("wind");
        assertThat(mix(Biome.ALPINE, 13, 0, 1, 0)).containsKey("high_gust");
        assertThat(mix(Biome.FOREST, 13, 1, 0, 0)).doesNotContainKey("birds_day").containsKey("rain");
        assertThat(mix(Biome.CAVE, 13, 1, 0, 0).get("rain").gain())
                .isLessThan(mix(Biome.FOREST, 13, 1, 0, 0).get("rain").gain());
        assertThat(mix(Biome.CAVE, 13, 1, 0, 0).get("drips").gain())
                .isGreaterThan(mix(Biome.CAVE, 13, 0, 0, 0).get("drips").gain());
        double prev = Double.MAX_VALUE;
        for (double rain : LEVELS) {
            double lp = mix(Biome.GRASSLAND, 13, rain, 0, 0).get("wind").lowpassHz();
            assertThat(lp).isLessThan(prev);
            prev = lp;
        }
        assertThat(mix(Biome.CAVE, 13, 0, 0, 0).get("room_tone").lowpassHz()).isEqualTo(3000.0);
    }

    @Test
    void headroomScalesProportionallyWhenTheBedIsFull() {
        List<AmbienceLayer> loud = BiomeAmbience.mix(new AmbienceState(Biome.COAST, 13, 1, 1, 1));
        double sum = loud.stream().mapToDouble(AmbienceLayer::gain).sum();
        assertThat(sum).isCloseTo(BiomeAmbience.HEADROOM, org.assertj.core.data.Offset.offset(0.005));
        Map<String, AmbienceLayer> m = mix(Biome.COAST, 13, 1, 1, 1);
        assertThat(m.get("surf").gain() / m.get("water").gain()).isCloseTo(0.9 / 0.6, org.assertj.core.data.Offset.offset(0.01));
        List<AmbienceLayer> quiet = BiomeAmbience.mix(new AmbienceState(Biome.DESERT, 1, 0, 0, 0));
        assertThat(quiet).extracting(AmbienceLayer::id).containsExactly("wind");
        assertThat(quiet.get(0).gain()).isEqualTo(0.15);
    }

    @Test
    void daylightCurvePeaksAtOnePmAndIsDarkAtNight() {
        assertThat(BiomeAmbience.daylight(13)).isEqualTo(1.0);
        assertThat(BiomeAmbience.daylight(1)).isZero();
        for (int h = 0; h < 24; h++) {
            assertThat(BiomeAmbience.daylight(h)).isBetween(0.0, 1.0);
            assertThat(BiomeAmbience.daylight(13 + h % 12)).isCloseTo(BiomeAmbience.daylight(13 - h % 12),
                    org.assertj.core.data.Offset.offset(1e-12));
        }
    }

    @Test
    void stateClampsAndWraps() {
        AmbienceState s = new AmbienceState(Biome.FOREST, -1, 2, -3, Double.NaN);
        assertThat(s.hour()).isEqualTo(23.0);
        assertThat(s.rain()).isEqualTo(1.0);
        assertThat(s.wind()).isZero();
        assertThat(s.waterNear()).isZero();
        assertThat(new AmbienceState(Biome.FOREST, 48.5, 0, 0, 0).hour()).isEqualTo(0.5);
        assertThat(BiomeAmbience.mix(new AmbienceState(Biome.WETLAND, 37, 0.3, 0.3, 0.3)))
                .isEqualTo(BiomeAmbience.mix(new AmbienceState(Biome.WETLAND, 13, 0.3, 0.3, 0.3)));
        assertThatThrownBy(() -> new AmbienceState(null, 0, 0, 0, 0)).isInstanceOf(RuntimeException.class);
        assertThatThrownBy(() -> BiomeAmbience.mix(s).add(null)).isInstanceOf(UnsupportedOperationException.class);
    }
}
