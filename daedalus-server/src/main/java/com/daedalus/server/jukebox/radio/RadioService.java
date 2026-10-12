// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox.radio;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.LongSupplier;

/**
 * The jukebox's radio: Radio Browser look-ups around the listener, ordered local FM first ({@link RadioRanking}).
 * The look-ups port ComputerPets' {@code searchParams} / {@code localAreaParams} / {@code radioSearchUrls}, plus a
 * coordinate search (Radio Browser's geo_lat/geo_long/geo_distance) when the browser shares a location.
 *
 * <p>Every station handed to a client is remembered by id, so the stream proxy only ever fetches a URL the directory
 * itself returned: the proxy is never an open relay.
 */
public final class RadioService {

    static final int LIMIT = 60;
    static final int MAX_RESULTS = 40;
    static final long TTL_MS = 10 * 60_000;
    static final int MAX_KNOWN = 5_000;

    public record Lineup(RadioArea area, List<RadioRanking.Ranked> stations, String note) {}

    private final RadioDirectory directory;
    private final LongSupplier clock;
    private final Map<String, Cached> cache = new ConcurrentHashMap<>();
    private final Map<String, String> known = new ConcurrentHashMap<>();   // station id -> stream URL

    private record Cached(long at, List<RadioStation> stations) {}

    public RadioService(RadioDirectory directory, LongSupplier clock) {
        this.directory = directory;
        this.clock = clock;
    }

    /** The search paths for an area, most local first. Empty area: the country's popular list, else the world's. */
    static List<String> searches(RadioArea a) {
        List<String> out = new ArrayList<>();
        if (a.hasCoords()) {
            out.add(path(Map.of("geo_lat", fmt(a.lat()), "geo_long", fmt(a.lon()),
                    "geo_distance", String.valueOf((long) (RadioRanking.LOCAL_KM * 1000)))));
        }
        if (a.hasPlace()) {   // ComputerPets: localAreaParams, then the city as a name
            Map<String, String> local = new LinkedHashMap<>();
            if (!a.city().isEmpty()) local.put("city", a.city());
            if (!a.state().isEmpty()) local.put("state", a.state());
            if (!a.countrycode().isEmpty()) local.put("countrycode", a.countrycode());
            out.add(path(local));
            if (!a.city().isEmpty()) {
                Map<String, String> named = new LinkedHashMap<>();
                named.put("name", a.city());
                if (!a.countrycode().isEmpty()) named.put("countrycode", a.countrycode());
                out.add(path(named));
            }
            if (!a.state().isEmpty() && !a.city().isEmpty()) {   // the whole state, for "other local options"
                Map<String, String> st = new LinkedHashMap<>();
                st.put("state", a.state());
                if (!a.countrycode().isEmpty()) st.put("countrycode", a.countrycode());
                out.add(path(st));
            }
        }
        if (!a.countrycode().isEmpty()) out.add(path(Map.of("countrycode", a.countrycode())));
        if (out.isEmpty()) out.add(path(Map.of()));
        return out.stream().distinct().limit(4).toList();
    }

    /** ComputerPets' searchParams: hide broken streams, most-clicked first; values capped at 40 chars. */
    static String path(Map<String, String> extra) {
        Map<String, String> p = new LinkedHashMap<>();
        p.put("limit", String.valueOf(LIMIT));
        p.put("hidebroken", "true");
        p.put("order", "clickcount");
        p.put("reverse", "true");
        extra.forEach((k, v) -> { if (v != null && !v.isEmpty()) p.put(k, v.length() > 40 ? v.substring(0, 40) : v); });
        StringBuilder b = new StringBuilder("/json/stations/search?");
        p.forEach((k, v) -> b.append(b.charAt(b.length() - 1) == '?' ? "" : "&").append(k).append('=')
                .append(URLEncoder.encode(v, StandardCharsets.UTF_8)));
        return b.toString();
    }

    public Lineup lineup(RadioArea area) {
        List<List<RadioStation>> batches = new ArrayList<>();
        int failed = 0;
        List<String> paths = searches(area);
        for (String p : paths) {
            try {
                batches.add(fetch(p));
            } catch (RuntimeException e) {
                failed++;
            }
        }
        if (failed == paths.size()) throw new IllegalStateException("can't reach the radio directory");
        List<RadioRanking.Ranked> ranked = RadioRanking.rank(RadioRanking.merge(batches), area);
        if (ranked.size() > MAX_RESULTS) ranked = ranked.subList(0, MAX_RESULTS);
        if (known.size() > MAX_KNOWN) known.clear();
        for (RadioRanking.Ranked r : ranked) known.put(r.station().id(), r.station().url());
        boolean placeless = !area.hasCoords() && !area.hasPlace();   // nothing, or only a language-derived country
        String note = placeless ? "No location: popular stations. Share your location or type a city for local FM."
                : ranked.isEmpty() ? "No stations found here." : ranked.get(0).tier() == RadioRanking.Tier.LOCAL_FM ? ""
                : "No local FM found: showing the nearest options.";
        return new Lineup(area, List.copyOf(ranked), note);
    }

    /** The stream URL for a station this server has listed, never anything else. */
    public Optional<String> streamOf(String id) {
        return Optional.ofNullable(id == null ? null : known.get(id));
    }

    private List<RadioStation> fetch(String path) {
        long now = clock.getAsLong();
        Cached c = cache.get(path);
        if (c != null && now - c.at() < TTL_MS) return c.stations();
        List<RadioStation> s = directory.search(path);
        if (cache.size() > 500) cache.clear();
        cache.put(path, new Cached(now, s));
        return s;
    }

    private static String fmt(double d) {
        return String.format(Locale.ROOT, "%.4f", d);
    }
}
