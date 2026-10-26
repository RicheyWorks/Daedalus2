// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;
import java.util.function.LongSupplier;
import java.util.regex.Pattern;

/**
 * Who is walking around in each world right now (ADR-039): position, heading, animation and look.
 *
 * <p>Clients report themselves a few times a second. The service keeps the latest report per player,
 * hands every accepted report to a listener (the STOMP topic), and forgets players it has not heard
 * from for {@link #STALE_MS}, telling the listener they left. Players are known by an opaque id: a hash
 * of who they are (the signed-in subject, or the tab's own id when nobody is signed in), so the topic
 * never shows a subject or a wallet address.
 *
 * <p>Nothing here touches the world's cubes. Presence is advisory, so a bad report is dropped rather
 * than fixed, and a world holds at most {@link #MAX_PER_WORLD} players.
 */
public final class PresenceService {

    /** A player not heard from for this long has left. */
    public static final long STALE_MS = 15_000;
    /** Players shown per world; a newcomer beyond this is turned away until someone leaves. */
    public static final int MAX_PER_WORLD = 64;
    /** Positions are clamped to the world's build volume and a margin around it. */
    public static final double MAX_COORD = 100_000;
    public static final int MAX_NAME = 24;

    /** The look keys a player may set, and what each value must look like. */
    public static final Map<String, Pattern> LOOK = Map.of(
            "skin", Pattern.compile("#[0-9a-fA-F]{6}"),
            "shirt", Pattern.compile("#[0-9a-fA-F]{6}"),
            "pants", Pattern.compile("#[0-9a-fA-F]{6}"),
            "hat", Pattern.compile("none|cap|crown|halo|horns|tophat|wizard"),
            "back", Pattern.compile("none|cape|wings|backpack|jetpack"));

    public enum Anim { IDLE, WALK, RUN, JUMP, FLY, SWIM, WAVE, DANCE, SIT }

    public enum Kind { MOVE, LEAVE }

    /** One player's latest state, as the topic shows it. */
    public record Player(String id, String name, double x, double y, double z, double yaw, Anim anim,
                         Map<String, String> look, long at) {
        public Player { look = look == null ? Map.of() : Map.copyOf(look); }
    }

    /** What the topic carries. */
    public record Frame(String worldId, Kind kind, Player player) {
    }

    /** What a client reports. */
    public record Report(String name, Double x, Double y, Double z, Double yaw, String anim, Map<String, String> look) {
        // Preserve invalid/null entries until report() can return its normal refusal result.
        public Report { look = look == null ? null : Collections.unmodifiableMap(new LinkedHashMap<>(look)); }
    }

    /** Why a report was turned away, or null when it was accepted. */
    public record Result(Player player, String refused) {
        public boolean ok() {
            return refused == null;
        }
    }

    private final Map<String, Map<String, Player>> worlds = new ConcurrentHashMap<>();
    private final LongSupplier clock;
    private final Consumer<Frame> listener;

    public PresenceService(LongSupplier clock, Consumer<Frame> listener) {
        this.clock = clock;
        this.listener = listener;
    }

    /** The opaque id the topic shows for this caller: never the subject itself. */
    public static String playerId(String subject, String tab) {
        String who = (subject == null || subject.isBlank() ? "guest" : subject) + "|" + (tab == null ? "" : tab);
        try {
            byte[] h = MessageDigest.getInstance("SHA-256").digest(who.getBytes(StandardCharsets.UTF_8));
            return "p-" + HexFormat.of().formatHex(h, 0, 6);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    /** Take a report: accepted ones replace the player's state and go to the listener. */
    public Result report(String worldId, String playerId, Report r) {
        sweep(worldId);
        if (r == null || r.x() == null || r.y() == null || r.z() == null) {
            return new Result(null, "x, y and z are required");
        }
        for (double v : new double[] {r.x(), r.y(), r.z(), r.yaw() == null ? 0.0 : r.yaw()}) {
            if (!Double.isFinite(v)) {
                return new Result(null, "coordinates must be finite numbers");
            }
        }
        if (Math.abs(r.x()) > MAX_COORD || Math.abs(r.y()) > MAX_COORD || Math.abs(r.z()) > MAX_COORD) {
            return new Result(null, "position is outside the world");
        }
        Anim anim;
        try {
            anim = r.anim() == null ? Anim.IDLE : Anim.valueOf(r.anim().trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            return new Result(null, "unknown anim " + r.anim());
        }
        Map<String, String> look = new TreeMap<>();
        if (r.look() != null) {
            for (Map.Entry<String, String> e : r.look().entrySet()) {
                Pattern p = e.getKey() == null ? null : LOOK.get(e.getKey());
                if (p == null) {
                    return new Result(null, "unknown look key " + e.getKey());
                }
                if (e.getValue() == null || !p.matcher(e.getValue()).matches()) {
                    return new Result(null, "bad value for look." + e.getKey());
                }
                look.put(e.getKey(), e.getValue().toLowerCase(Locale.ROOT));
            }
        }
        Map<String, Player> here = worlds.computeIfAbsent(worldId, k -> new LinkedHashMap<>());
        Player p;
        synchronized (here) {
            if (!here.containsKey(playerId) && here.size() >= MAX_PER_WORLD) {
                return new Result(null, "this world is full (" + MAX_PER_WORLD + " players)");
            }
            double yaw = r.yaw() == null ? 0.0 : Math.IEEEremainder(r.yaw(), 2 * Math.PI);
            p = new Player(playerId, cleanName(r.name()), r.x(), r.y(), r.z(), yaw, anim, Map.copyOf(look),
                    clock.getAsLong());
            here.put(playerId, p);
        }
        listener.accept(new Frame(worldId, Kind.MOVE, p));
        return new Result(p, null);
    }

    /** The player leaves now (closing the tab, switching worlds). Returns whether they were here. */
    public boolean leave(String worldId, String playerId) {
        Map<String, Player> here = worlds.get(worldId);
        if (here == null) {
            return false;
        }
        Player gone;
        synchronized (here) {
            gone = here.remove(playerId);
        }
        if (gone != null) {
            listener.accept(new Frame(worldId, Kind.LEAVE, gone));
        }
        return gone != null;
    }

    /** Everyone in the world now, oldest arrival first. */
    public List<Player> who(String worldId) {
        sweep(worldId);
        Map<String, Player> here = worlds.get(worldId);
        if (here == null) {
            return List.of();
        }
        synchronized (here) {
            return List.copyOf(here.values());
        }
    }

    /** Forget players not heard from for STALE_MS, telling the listener each one left. */
    public int sweep(String worldId) {
        Map<String, Player> here = worlds.get(worldId);
        if (here == null) {
            return 0;
        }
        long now = clock.getAsLong();
        List<Player> gone = new ArrayList<>();
        synchronized (here) {
            here.values().removeIf(p -> {
                boolean stale = now - p.at() > STALE_MS;
                if (stale) {
                    gone.add(p);
                }
                return stale;
            });
        }
        gone.forEach(p -> listener.accept(new Frame(worldId, Kind.LEAVE, p)));
        return gone.size();
    }

    static String cleanName(String raw) {
        if (raw == null) {
            return "guest";
        }
        StringBuilder b = new StringBuilder();
        raw.strip().codePoints()
                .filter(c -> !Character.isISOControl(c) && "<>&\"'`".indexOf(c) < 0)
                .limit(MAX_NAME)
                .forEach(b::appendCodePoint);
        String s = b.toString().strip();
        return s.isEmpty() ? "guest" : s;
    }
}
