// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox.radio;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Orders stations so <b>local FM always comes first</b>. Three tiers, decided before any score:
 * <ol>
 *   <li>{@link Tier#LOCAL_FM}: FM stations within {@link #LOCAL_KM} of the listener, or, with no coordinates, in the
 *       named city (or state when no city was named); nearest first</li>
 *   <li>{@link Tier#LOCAL}: every other local station (AM, unknown band, online-only streamed from nearby)</li>
 *   <li>{@link Tier#ELSEWHERE}: the rest, by ComputerPets' {@code rankStations} score</li>
 * </ol>
 * The score and the haversine distance are ported from ComputerPets (house-music.js {@code rankStations},
 * {@code kmBetween}, {@code mergeStations}).
 */
public final class RadioRanking {

    public static final double LOCAL_KM = 120;

    public enum Tier { LOCAL_FM, LOCAL, ELSEWHERE }

    public record Ranked(RadioStation station, Tier tier, Double km, int score) {}

    private RadioRanking() {}

    /** ComputerPets' mergeStations: first occurrence of each id wins. */
    public static List<RadioStation> merge(List<List<RadioStation>> batches) {
        Map<String, RadioStation> seen = new LinkedHashMap<>();
        for (List<RadioStation> b : batches) for (RadioStation s : b) seen.putIfAbsent(s.id(), s);
        return new ArrayList<>(seen.values());
    }

    /** ComputerPets' kmBetween (haversine, 6371 km). Null when any coordinate is missing. */
    public static Double km(Double aLat, Double aLon, Double bLat, Double bLon) {
        if (aLat == null || aLon == null || bLat == null || bLon == null) return null;
        double dLat = Math.toRadians(bLat - aLat), dLon = Math.toRadians(bLon - aLon);
        double s = Math.sin(dLat / 2) * Math.sin(dLat / 2)
                + Math.cos(Math.toRadians(aLat)) * Math.cos(Math.toRadians(bLat)) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
        return 6371 * 2 * Math.atan2(Math.sqrt(s), Math.sqrt(1 - s));
    }

    public static Tier tier(RadioStation s, RadioArea here, Double km) {
        boolean local;
        if (km != null) {
            local = km <= LOCAL_KM;
        } else if (here.hasPlace()) {
            String hay = (s.city() + " " + s.state() + " " + s.name()).toLowerCase(Locale.ROOT);
            boolean sameCountry = here.countrycode().isEmpty() || here.countrycode().equalsIgnoreCase(s.countrycode());
            local = sameCountry && (!here.city().isEmpty() ? hay.contains(here.city().toLowerCase(Locale.ROOT))
                    : hay.contains(here.state().toLowerCase(Locale.ROOT)));
        } else {
            local = false;
        }
        if (!local) return Tier.ELSEWHERE;
        return s.band() == RadioStation.Band.FM ? Tier.LOCAL_FM : Tier.LOCAL;
    }

    /** ComputerPets' rankStations score (query tokens, place, distance bands), with no free-text query. */
    static int score(RadioStation st, RadioArea here, Double km) {
        String hay = (st.name() + " " + st.tags() + " " + st.state() + " " + st.country() + " " + st.countrycode() + " "
                + st.city()).toLowerCase(Locale.ROOT);
        int score = 0;
        if (!here.city().isEmpty() && hay.contains(here.city().toLowerCase(Locale.ROOT))) score += 4 + 2;
        if (!here.state().isEmpty() && hay.contains(here.state().toLowerCase(Locale.ROOT))) score += 3 + 2;
        if (!here.countrycode().isEmpty() && here.countrycode().equalsIgnoreCase(st.countrycode())) score += 2;
        if (km != null) {
            if (km <= 80) score += 6;
            else if (km <= 250) score += 3;
            else if (km <= 600) score += 1;
        }
        return score;
    }

    /** Local FM first, then other local, then everything else. Stable within equal keys (keeps popularity order). */
    public static List<Ranked> rank(List<RadioStation> stations, RadioArea here) {
        List<Ranked> rows = new ArrayList<>();
        for (RadioStation s : stations) {
            Double km = here.hasCoords() ? km(here.lat(), here.lon(), s.lat(), s.lon()) : null;
            rows.add(new Ranked(s, tier(s, here, km), km, score(s, here, km)));
        }
        rows.sort(Comparator.comparing(Ranked::tier)
                .thenComparingDouble(r -> r.tier() == Tier.ELSEWHERE || r.km() == null ? Double.MAX_VALUE : r.km())
                .thenComparingInt(r -> -r.score()));
        return rows;
    }
}
