package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Biome + time + weather -> ordered list of ambience layers. Deterministic, engine-neutral. */
public final class BiomeAmbience {
    /** Total gain ceiling so beds never clip when summed. */
    public static final double HEADROOM = 0.9;

    private BiomeAmbience() {
    }

    /** Daylight 0..1, a smooth curve peaking at 13:00. */
    public static double daylight(double hour) {
        return Math.max(0, Math.cos((hour - 13) / 24.0 * 2 * Math.PI) * 1.25 - 0.25);
    }

    /** Builds the mix; layers with zero gain are dropped and the rest are sorted by id. */
    public static List<AmbienceLayer> mix(AmbienceState s) {
        double day = Math.min(1, daylight(s.hour()));
        double night = 1 - day;
        double muffle = 18000 - 12000 * s.rain();
        List<double[]> raw = new ArrayList<>();
        List<String> ids = new ArrayList<>();
        add(ids, raw, "wind", 0.15 + 0.6 * s.wind() * windiness(s.biome()), muffle, 0);
        add(ids, raw, "rain", 0.7 * s.rain() * (s.biome() == Biome.CAVE ? 0.2 : 1), 12000, s.rain());
        add(ids, raw, "water", 0.6 * s.waterNear(), muffle, 0);
        switch (s.biome()) {
            case FOREST -> {
                add(ids, raw, "birds_day", 0.5 * day * (1 - s.rain()), muffle, day);
                add(ids, raw, "leaves", 0.3 * s.wind(), muffle, s.wind());
                add(ids, raw, "owls_night", 0.25 * night, muffle, 0.2 * night);
            }
            case GRASSLAND -> {
                add(ids, raw, "insects_day", 0.4 * day, muffle, day);
                add(ids, raw, "crickets_night", 0.45 * night, muffle, night);
            }
            case WETLAND -> {
                add(ids, raw, "frogs", 0.5 * (0.3 + 0.7 * night) * (0.6 + 0.4 * s.rain()), muffle, night);
                add(ids, raw, "reeds", 0.25 * s.wind(), muffle, s.wind());
            }
            case COAST -> {
                add(ids, raw, "surf", 0.6 + 0.3 * s.wind(), muffle, 0);
                add(ids, raw, "gulls", 0.3 * day, muffle, 0.4 * day);
            }
            case DESERT -> add(ids, raw, "sand_hiss", 0.3 * s.wind(), muffle, s.wind());
            case ALPINE -> add(ids, raw, "high_gust", 0.35 * s.wind(), muffle, s.wind());
            case CAVE -> {
                add(ids, raw, "drips", 0.35 + 0.3 * s.rain(), 8000, 0.3 + 0.5 * s.rain());
                add(ids, raw, "room_tone", 0.3, 3000, 0);
            }
            default -> throw new IllegalStateException("unhandled biome " + s.biome());
        }
        double sum = 0;
        for (double[] r : raw) {
            sum += r[0];
        }
        double k = sum > HEADROOM ? HEADROOM / sum : 1;
        List<AmbienceLayer> out = new ArrayList<>();
        for (int i = 0; i < raw.size(); i++) {
            double[] r = raw.get(i);
            out.add(new AmbienceLayer(ids.get(i), round3(r[0] * k), Math.round(r[1]), round3(r[2])));
        }
        out.sort((a, b) -> a.id().compareTo(b.id()));
        return Collections.unmodifiableList(out);
    }

    private static double windiness(Biome b) {
        return switch (b) {
            case ALPINE, COAST -> 1.0;
            case DESERT, GRASSLAND -> 0.8;
            case FOREST, WETLAND -> 0.5;
            case CAVE -> 0.1;
        };
    }

    private static void add(List<String> ids, List<double[]> raw, String id, double gain, double lp, double density) {
        if (gain > 1e-6) {
            ids.add(id);
            raw.add(new double[] {gain, lp, Math.max(0, Math.min(1, density))});
        }
    }

    private static double round3(double v) {
        return Math.round(v * 1000.0) / 1000.0;
    }
}
