// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox.radio;

import com.fasterxml.jackson.databind.JsonNode;

import java.net.URI;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * One Radio Browser station. {@link #parse} ports ComputerPets' {@code parseStations} + {@code safeStream}: only
 * http(s) streams with no userinfo, names trimmed, fields length-capped. {@link #band()} is new for the jukebox.
 */
public record RadioStation(String id, String name, String url, String tags, String city, String state, String country,
                           String countrycode, Double lat, Double lon) {

    public enum Band { FM, AM, OTHER }

    private static final Pattern FREQ = Pattern.compile("(?<![\\d.])(\\d{2,4}(?:\\.\\d{1,2})?)(?![\\d.])");
    private static final Pattern FM_WORD = Pattern.compile("(?i)(?<![a-z])(fm)(?![a-z])|-fm\\b");
    private static final Pattern AM_WORD = Pattern.compile("(?i)(?<![a-z])(am)(?![a-z])|-am\\b");

    /** ComputerPets' safeStream: http(s) only, no credentials in the URL. Empty when unsafe. */
    public static String safeStream(String raw) {
        try {
            URI u = URI.create(raw == null ? "" : raw.trim());
            String scheme = u.getScheme() == null ? "" : u.getScheme().toLowerCase(Locale.ROOT);
            if (!scheme.equals("http") && !scheme.equals("https")) return "";
            if (u.getUserInfo() != null || u.getHost() == null) return "";
            return u.toString();
        } catch (IllegalArgumentException e) {
            return "";
        }
    }

    public static List<RadioStation> parse(JsonNode json) {
        List<RadioStation> out = new ArrayList<>();
        if (json == null || !json.isArray()) return out;
        for (JsonNode row : json) {
            if (!row.isObject()) continue;
            String url = safeStream(text(row, "url_resolved").isEmpty() ? text(row, "url") : text(row, "url_resolved"));
            String name = cap(text(row, "name").replaceAll("\\s+", " ").trim(), 72);
            if (url.isEmpty() || name.isEmpty()) continue;
            String id = text(row, "stationuuid");
            if (id.isEmpty()) id = text(row, "changeuuid");
            if (id.isEmpty()) id = name;
            out.add(new RadioStation(cap(id, 64), name, url, cap(text(row, "tags"), 60),
                    cap(text(row, "state").isEmpty() ? text(row, "city") : text(row, "state"), 40),   // as ComputerPets
                    cap(text(row, "state"), 40), cap(text(row, "country"), 40), cap(text(row, "countrycode"), 4),
                    num(row, "geo_lat"), num(row, "geo_long")));
        }
        return out;
    }

    /** FM by its name/tags ("FM", "-FM", or a frequency in 87.5–108.0); AM by "AM" or 530–1710; else unknown. */
    public Band band() {
        String hay = name + " " + tags;
        if (FM_WORD.matcher(hay).find()) return Band.FM;
        if (AM_WORD.matcher(name).find()) return Band.AM;
        Matcher m = FREQ.matcher(name);
        while (m.find()) {
            double f = Double.parseDouble(m.group(1));
            if (f >= 87.5 && f <= 108.0 && m.group(1).contains(".")) return Band.FM;
            if (f >= 530 && f <= 1710 && !m.group(1).contains(".")) return Band.AM;
        }
        return Band.OTHER;
    }

    public boolean https() { return url.startsWith("https:"); }

    private static String text(JsonNode n, String f) {
        JsonNode v = n.get(f);
        return v == null || v.isNull() ? "" : v.asText("");
    }

    private static Double num(JsonNode n, String f) {
        JsonNode v = n.get(f);
        if (v == null || v.isNull()) return null;
        double d = v.asDouble(Double.NaN);
        return Double.isNaN(d) ? null : d;
    }

    private static String cap(String s, int max) {
        return s.length() > max ? s.substring(0, max) : s;
    }
}
