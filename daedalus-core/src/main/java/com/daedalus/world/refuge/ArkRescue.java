// SPDX-License-Identifier: MIT
package com.daedalus.world.refuge;

import com.daedalus.world.ecology.Community;
import com.daedalus.world.ecology.Guild;
import com.daedalus.world.ecology.Habitat;
import com.daedalus.world.ecology.Hold;
import com.daedalus.world.ecology.Species;
import com.daedalus.world.ecology.SpeciesCanon;
import java.util.Collections;
import java.util.EnumMap;
import java.util.Map;
import java.util.Objects;
import java.util.TreeMap;

/** Unicorn-authorized rescue transfers using the existing canon, communities and ark holds.
 * Owner serializes all calls under the same world lock as ArkFleet/WorldService.
 * Persist source, hold, destination and receipt in one transaction before publishing quest events.
 * This class is pure domain code; it does not assert that a server transaction or voyage occurred.
 */
public final class ArkRescue {
    public static final int MAX_RECEIPTS = 4096;
    public static final int MAX_PER_TRANSFER = 25;
    public enum Kind { BOARD, LAND }
    public record Receipt(String eventId, String questId, String arkId, Kind kind,
                          String speciesKey, int count) {}
    public enum Result { APPLIED, REPLAY, CONFLICT, STALE, CAPACITY }
    private final SpeciesCanon canon;
    private final TreeMap<String, Receipt> receipts = new TreeMap<>();

    public ArkRescue(SpeciesCanon canon) { this.canon = Objects.requireNonNull(canon); }
    public Map<String, Receipt> receipts() { return Collections.unmodifiableMap(new TreeMap<>(receipts)); }
    private static boolean identity(String s) {
        return s != null && !s.isEmpty() && s.length() <= 100
                && s.chars().allMatch(c -> c > 32 && c != 127);
    }
    private static boolean finiteCount(double n) { return Double.isFinite(n) && n >= 0 && n <= 1_000_000; }

    /** A plan binds the actual source/hold objects and observed balances; callers cannot construct one. */
    public static final class Plan {
        private final ArkRescue owner;
        private final Receipt receipt;
        private final Map<String, Double> communitySnapshot, holdSnapshot;
        private final Community community;
        private final Hold hold;
        private final double communityBefore, holdBefore;
        private Plan(ArkRescue owner, Receipt receipt, Community community, Hold hold, double communityBefore, double holdBefore) {
            this.owner = owner;
            communitySnapshot = Map.copyOf(community.abundance()); holdSnapshot = Map.copyOf(hold.cargo());
            this.receipt = receipt; this.community = community; this.hold = hold;
            this.communityBefore = communityBefore; this.holdBefore = holdBefore;
        }
        public Receipt receipt() { return receipt; }
        public double communityAfter() { return communityBefore + (receipt.kind() == Kind.BOARD ? -receipt.count() : receipt.count()); }
        public double holdAfter() { return holdBefore + (receipt.kind() == Kind.BOARD ? receipt.count() : -receipt.count()); }
    }

    /** Preserve guild carrying capacity across every species, including plants, fungi and marine life. */
    private boolean room(Map<String, Double> current, Species incoming, int count, Habitat habitat) {
        EnumMap<Guild, Double> occupied = new EnumMap<>(Guild.class);
        for (var entry : current.entrySet()) {
            Species s = canon.byKey(entry.getKey());
            if (s == null || !finiteCount(entry.getValue())) return false;
            occupied.merge(s.guild(), entry.getValue() / Community.density(s.size()), Double::sum);
        }
        double cells = habitat.of(incoming.guild());
        return Double.isFinite(cells) && cells > 0
                && occupied.getOrDefault(incoming.guild(), 0.0) + count / Community.density(incoming.size()) <= cells;
    }

    /** Host verifies quest authorization, correct dock, stable ark identity and a stationary vessel. */
    public Plan prepare(String eventId, String questId, String arkId, Kind kind, String speciesKey,
                        int count, Community community, Hold hold, Habitat targetHabitat,
                        boolean hostQuestAndDockVerified) {
        if (!hostQuestAndDockVerified || !identity(eventId) || !identity(questId) || !identity(arkId)
                || !identity(speciesKey) || kind == null || count <= 0 || count > MAX_PER_TRANSFER
                || community == null || hold == null || targetHabitat == null) return null;
        Species species = canon.byKey(speciesKey);
        if (species == null) return null;
        double local = community.count(speciesKey), aboard = hold.cargo().getOrDefault(speciesKey, 0.0);
        if (!finiteCount(local) || !finiteCount(aboard)) return null;
        Receipt receipt = new Receipt(eventId, questId, arkId, kind, speciesKey, count);
        // Replays are represented without requiring the old pre-transfer balances to still exist.
        if (receipts.containsKey(eventId)) return new Plan(this, receipt, community, hold, local, aboard);
        if (receipts.size() >= MAX_RECEIPTS) return null;
        if (kind == Kind.BOARD) {
            if (local < count || aboard > 1_000_000 - count || !room(hold.cargo(), species, count, targetHabitat)) return null;
            if (!hold.cargo().containsKey(speciesKey) && hold.cargo().size() >= Hold.CAPACITY) return null;
        } else {
            if (aboard < count || local > 1_000_000 - count || !room(community.abundance(), species, count, targetHabitat)) return null;
        }
        return new Plan(this, receipt, community, hold, local, aboard);
    }

    /** Apply under the world lock; the host owns atomic storage and must not publish on failure. */
    public Result apply(Plan plan) {
        if (plan == null || plan.owner != this) return Result.CONFLICT;
        Receipt old = receipts.get(plan.receipt.eventId());
        if (old != null) return old.equals(plan.receipt) ? Result.REPLAY : Result.CONFLICT;
        if (receipts.size() >= MAX_RECEIPTS) return Result.CAPACITY;
        String key = plan.receipt.speciesKey();
        if (!plan.community.abundance().equals(plan.communitySnapshot) || !plan.hold.cargo().equals(plan.holdSnapshot)
                || Double.compare(plan.community.count(key), plan.communityBefore) != 0
                || Double.compare(plan.hold.cargo().getOrDefault(key, 0.0), plan.holdBefore) != 0) return Result.STALE;
        plan.community.put(key, plan.communityAfter()); plan.hold.put(key, plan.holdAfter());
        receipts.put(plan.receipt.eventId(), plan.receipt); return Result.APPLIED;
    }

    public boolean restoreReceipts(Map<String, Receipt> saved) {
        if (!receipts.isEmpty() || saved == null || saved.size() > MAX_RECEIPTS) return false;
        TreeMap<String, Receipt> candidate = new TreeMap<>();
        for (var entry : saved.entrySet()) {
            Receipt r = entry.getValue();
            if (r == null || !identity(entry.getKey()) || !entry.getKey().equals(r.eventId())
                    || !identity(r.questId()) || !identity(r.arkId()) || r.kind() == null
                    || canon.byKey(r.speciesKey()) == null || r.count() <= 0 || r.count() > MAX_PER_TRANSFER) return false;
            candidate.put(entry.getKey(), r);
        }
        receipts.putAll(candidate); return true;
    }

    /** Quest statistics distinguish boarding from actual safe landings and include every guild. */
    public Map<Guild, Integer> landedByGuild(String questId) {
        EnumMap<Guild, Integer> out = new EnumMap<>(Guild.class);
        for (Guild g : Guild.values()) out.put(g, 0);
        for (Receipt r : receipts.values()) if (r.kind() == Kind.LAND && r.questId().equals(questId))
            out.merge(canon.byKey(r.speciesKey()).guild(), r.count(), Integer::sum);
        return Collections.unmodifiableMap(out);
    }
}
