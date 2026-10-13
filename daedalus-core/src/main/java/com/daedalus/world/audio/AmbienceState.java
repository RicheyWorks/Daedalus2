package com.daedalus.world.audio;

/**
 * Inputs to the ambience mixer.
 *
 * @param biome biome under the listener
 * @param hour local hour 0..24
 * @param rain rain intensity 0..1
 * @param wind wind strength 0..1
 * @param waterNear 0..1 proximity to running water (stream/cistern chain)
 */
public record AmbienceState(Biome biome, double hour, double rain, double wind, double waterNear) {
    /** Clamps inputs. */
    public AmbienceState {
        if (biome == null) {
            throw new IllegalArgumentException("biome required");
        }
        hour = ((hour % 24) + 24) % 24;
        rain = clamp(rain);
        wind = clamp(wind);
        waterNear = clamp(waterNear);
    }

    private static double clamp(double v) {
        return Double.isNaN(v) ? 0 : Math.max(0, Math.min(1, v));
    }
}
