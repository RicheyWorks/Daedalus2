// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox.radio;

import java.util.Locale;
import java.util.Map;

/**
 * Where the listener is: a typed place ("Seattle, Washington, US") and/or browser coordinates.
 * Port of ComputerPets' {@code parseAreaPlace} / {@code countryCodeOf} (desktop/renderer/house-music.js).
 * ComputerPets never guesses a city the user did not name; neither does this. No location is a valid answer.
 */
public record RadioArea(String city, String state, String countrycode, Double lat, Double lon) {

    public static final RadioArea NONE = new RadioArea("", "", "", null, null);

    /** ComputerPets' COUNTRY_CODES, verbatim. */
    static final Map<String, String> COUNTRY_CODES = Map.ofEntries(
            Map.entry("united states", "US"), Map.entry("usa", "US"), Map.entry("us", "US"),
            Map.entry("united kingdom", "GB"), Map.entry("uk", "GB"), Map.entry("canada", "CA"),
            Map.entry("australia", "AU"), Map.entry("germany", "DE"), Map.entry("france", "FR"),
            Map.entry("japan", "JP"), Map.entry("ireland", "IE"), Map.entry("mexico", "MX"));

    public RadioArea {
        city = clean(city, 40);
        state = clean(state, 40);
        countrycode = clean(countrycode, 2).toUpperCase(Locale.ROOT);
        if (!countrycode.matches("[A-Z]{2}")) countrycode = "";
        if (lat != null && (lat.isNaN() || Math.abs(lat) > 90)) lat = null;
        if (lon != null && (lon.isNaN() || Math.abs(lon) > 180)) lon = null;
        if (lat == null || lon == null) { lat = null; lon = null; }
    }

    /** "City, State, Country" (any part optional, as ComputerPets parses it) plus optional coordinates and a fallback country. */
    public static RadioArea parse(String place, Double lat, Double lon, String fallbackCountry) {
        String[] bits = place == null ? new String[0] : place.split(",");
        String city = bits.length > 0 ? bits[0].trim() : "";
        String state = "", country = "";
        for (int i = 1; i < bits.length; i++) {
            String bit = bits[i].trim();
            if (!countryCodeOf(bit).isEmpty()) country = bit;
            else if (state.isEmpty()) state = bit;
        }
        String cc = countryCodeOf(country);
        if (cc.isEmpty()) cc = countryCodeOf(fallbackCountry);
        return new RadioArea(city, state, cc, lat, lon);
    }

    static String countryCodeOf(String raw) {
        String s = raw == null ? "" : raw.trim().toLowerCase(Locale.ROOT);
        if (s.isEmpty()) return "";
        if (COUNTRY_CODES.containsKey(s)) return COUNTRY_CODES.get(s);
        return s.matches("[a-z]{2}") ? s.toUpperCase(Locale.ROOT) : "";
    }

    public boolean hasCoords() { return lat != null; }

    public boolean hasPlace() { return !city.isEmpty() || !state.isEmpty(); }

    public boolean isEmpty() { return !hasCoords() && !hasPlace() && countrycode.isEmpty(); }

    private static String clean(String s, int max) {
        String t = s == null ? "" : s.replaceAll("[\\p{Cntrl}]", "").replaceAll("\\s+", " ").trim();
        return t.length() > max ? t.substring(0, max) : t;
    }
}
