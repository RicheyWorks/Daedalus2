// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.activity.ProgressionLedger;

import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.TreeMap;

/**
 * One front door for every finished game: hosts hand a game's own result to the router by activity id; the router
 * finds the registered G12 adapter, issues the receipt and settles it once through the {@link ProgressionLedger}
 * under that activity's {@link AwardPolicy} (inactive until the owner approves numbers). The router owns its
 * reference ledger; a persistent host keeps the same award keys.
 */
public final class ActivityRouter {

    private record Entry(ActivityResultAdapter<?> adapter, Class<?> resultType, AwardPolicy policy) { }

    private final Map<String, Entry> entries = new TreeMap<>();
    private final Object lock = new Object();
    private final ProgressionLedger ledger = new ProgressionLedger();
    private final java.util.List<String> journal = new java.util.ArrayList<>();
    private final java.util.Map<String, String> journalled = new java.util.HashMap<>();

    /** Learned points on a track for one life or colony instance. */
    public long total(String instanceId, String track) { return ledger.total(instanceId, track); }

    /** Contribution history for one instance, oldest first. */
    public List<ProgressionLedger.Award> history(String instanceId) { return ledger.history(instanceId); }

    /** The router with the three contest adapters (fishing, hornbacks, echo bells) and inactive policies. */
    public static ActivityRouter contest(com.daedalus.world.activity.ActivityMode mode) {
        ActivityRouter r = new ActivityRouter();
        r.register(new FishingCastAdapter(mode), FishingCastAdapter.Outing.class,
                AwardPolicy.inactive(FishingCastAdapter.ACTIVITY_ID, "mastery.scouting"));
        r.register(new HornbackPassageAdapter(mode), HornbackPassageAdapter.Passage.class,
                AwardPolicy.inactive(HornbackPassageAdapter.ACTIVITY_ID, "mastery.herding"));
        r.register(new EchoBellAdapter(mode), EchoBellAdapter.Listening.class,
                AwardPolicy.inactive(EchoBellAdapter.ACTIVITY_ID, "mastery.observation"));
        return r;
    }

    /**
     * Every landed contest game: the three from {@link #contest} plus G06 egg care, G11 catch, G14 mail route and
     * G16 assembly repair (contest G36), and G17 kennel water, G19 temper forge, G20 ashfall regrowth and
     * G27 fireline warden (contest G44), G26 kennel pantry and G40 herb chord garden (contest G55), G52 fog bell,
     * G60 wind chime, G64 drip cave and G35 squall cup (contest G74), and the Pythagoras ecology games G34 beaver
     * waters, G43 ark seed vault, G48 bee bloom, G58 trophic cascade and G71 salmon run (contest G83), and the
     * OddsReaper quests G56 keeper's ledger, G68 launch window, G77 rival book, G80 ark underwriter and G88 keeper's
     * tote (contest G95), all with inactive policies.
     */
    public static ActivityRouter contestAll(com.daedalus.world.activity.ActivityMode mode) {
        ActivityRouter r = contest(mode);
        r.register(new EggCareAdapter(mode), EggCareAdapter.Care.class,
                AwardPolicy.inactive(EggCareAdapter.ACTIVITY_ID, "mastery.nursery"));
        r.register(new CatchRallyAdapter(mode), CatchRallyAdapter.Rally.class,
                AwardPolicy.inactive(CatchRallyAdapter.ACTIVITY_ID, "mastery.play"));
        r.register(new MailRouteAdapter(mode), MailRouteAdapter.Round.class,
                AwardPolicy.inactive(MailRouteAdapter.ACTIVITY_ID, "mastery.logistics"));
        r.register(new AssemblyRepairAdapter(mode), AssemblyRepairAdapter.Repair.class,
                AwardPolicy.inactive(AssemblyRepairAdapter.ACTIVITY_ID, "mastery.restoration"));
        r.register(new KennelWaterAdapter(mode), KennelWaterAdapter.Watch.class,
                AwardPolicy.inactive(KennelWaterAdapter.ACTIVITY_ID, "mastery.husbandry"));
        r.register(new TemperForgeAdapter(mode), TemperForgeAdapter.Temper.class,
                AwardPolicy.inactive(TemperForgeAdapter.ACTIVITY_ID, "mastery.smithing"));
        r.register(new AshfallRegrowthAdapter(mode), AshfallRegrowthAdapter.Regrowth.class,
                AwardPolicy.inactive(AshfallRegrowthAdapter.ACTIVITY_ID, "mastery.regrowth"));
        r.register(new FirelineWardenAdapter(mode), FirelineWardenAdapter.Defence.class,
                AwardPolicy.inactive(FirelineWardenAdapter.ACTIVITY_ID, "mastery.firefighting"));
        r.register(new KennelPantryAdapter(mode), KennelPantryAdapter.Feeding.class,
                AwardPolicy.inactive(KennelPantryAdapter.ACTIVITY_ID, "mastery.husbandry"));
        r.register(new HerbGardenAdapter(mode), HerbGardenAdapter.Planting.class,
                AwardPolicy.inactive(HerbGardenAdapter.ACTIVITY_ID, "mastery.pollination"));
        r.register(new FogBellAdapter(mode), FogBellAdapter.Call.class,
                AwardPolicy.inactive(FogBellAdapter.ACTIVITY_ID, "mastery.observation"));
        r.register(new WindChimeAdapter(mode), WindChimeAdapter.Tuning.class,
                AwardPolicy.inactive(WindChimeAdapter.ACTIVITY_ID, "mastery.crafting"));
        r.register(new DripCaveAdapter(mode), DripCaveAdapter.Chorus.class,
                AwardPolicy.inactive(DripCaveAdapter.ACTIVITY_ID, "mastery.rhythm"));
        r.register(new SquallCupAdapter(mode), SquallCupAdapter.Cup.class,
                AwardPolicy.inactive(SquallCupAdapter.ACTIVITY_ID, "mastery.fishing"));
        r.register(new BeaverWatersAdapter(mode), BeaverWatersAdapter.Ponds.class,
                AwardPolicy.inactive(BeaverWatersAdapter.ACTIVITY_ID, "mastery.building"));
        r.register(new SeedVaultAdapter(mode), SeedVaultAdapter.Voyage.class,
                AwardPolicy.inactive(SeedVaultAdapter.ACTIVITY_ID, "mastery.seeding"));
        r.register(new BeeBloomAdapter(mode), BeeBloomAdapter.Season.class,
                AwardPolicy.inactive(BeeBloomAdapter.ACTIVITY_ID, "mastery.pollination"));
        r.register(new TrophicCascadeAdapter(mode), TrophicCascadeAdapter.Valley.class,
                AwardPolicy.inactive(TrophicCascadeAdapter.ACTIVITY_ID, "mastery.hunting"));
        r.register(new SalmonRunAdapter(mode), SalmonRunAdapter.Run.class,
                AwardPolicy.inactive(SalmonRunAdapter.ACTIVITY_ID, "mastery.fishing"));
        r.register(new KeepersLedgerAdapter(mode), KeepersLedgerAdapter.Ledger.class,
                AwardPolicy.inactive(KeepersLedgerAdapter.ACTIVITY_ID, "mastery.reckoning"));
        r.register(new LaunchWindowAdapter(mode), LaunchWindowAdapter.Launch.class,
                AwardPolicy.inactive(LaunchWindowAdapter.ACTIVITY_ID, "mastery.forecasting"));
        r.register(new RivalBookAdapter(mode), RivalBookAdapter.Scan.class,
                AwardPolicy.inactive(RivalBookAdapter.ACTIVITY_ID, "mastery.reckoning"));
        r.register(new ArkUnderwriterAdapter(mode), ArkUnderwriterAdapter.Season.class,
                AwardPolicy.inactive(ArkUnderwriterAdapter.ACTIVITY_ID, "mastery.reckoning"));
        r.register(new KeepersToteAdapter(mode), KeepersToteAdapter.Heat.class,
                AwardPolicy.inactive(KeepersToteAdapter.ACTIVITY_ID, "mastery.reckoning"));
        r.register(new RecordHuntAdapter(mode), RecordHuntAdapter.Hunt.class,
                AwardPolicy.inactive(RecordHuntAdapter.ACTIVITY_ID, "mastery.island-story"));
        r.register(new ChoirStonesAdapter(mode), ChoirStonesAdapter.Watch.class,
                AwardPolicy.inactive(ChoirStonesAdapter.ACTIVITY_ID, "mastery.island-story"));
        r.register(new FirstWeekAdapter(mode), FirstWeekAdapter.Week.class,
                AwardPolicy.inactive(FirstWeekAdapter.ACTIVITY_ID, "mastery.island-story"));
        r.register(new RootCellarAdapter(mode), RootCellarAdapter.Cellar.class,
                AwardPolicy.inactive(RootCellarAdapter.ACTIVITY_ID, "mastery.island-story"));
        r.register(new HomecomingSupperAdapter(mode), HomecomingSupperAdapter.Supper.class,
                AwardPolicy.inactive(HomecomingSupperAdapter.ACTIVITY_ID, "mastery.island-story"));
        r.register(new ThirteenthSongAdapter(mode), ThirteenthSongAdapter.Composing.class,
                AwardPolicy.inactive(ThirteenthSongAdapter.ACTIVITY_ID, "mastery.island-story"));
        r.register(new ThunderTowersAdapter(mode), ThunderTowersAdapter.Storm.class,
                AwardPolicy.inactive(ThunderTowersAdapter.ACTIVITY_ID, "mastery.listening"));
        r.register(new DopplerFlybyAdapter(mode), DopplerFlybyAdapter.Flyby.class,
                AwardPolicy.inactive(DopplerFlybyAdapter.ACTIVITY_ID, "mastery.listening"));
        r.register(new HullKnockAdapter(mode), HullKnockAdapter.Survey.class,
                AwardPolicy.inactive(HullKnockAdapter.ACTIVITY_ID, "mastery.listening"));
        r.register(new WaveOrganAdapter(mode), WaveOrganAdapter.Tide.class,
                AwardPolicy.inactive(WaveOrganAdapter.ACTIVITY_ID, "mastery.listening"));
        r.register(new KeepersCallAdapter(mode), KeepersCallAdapter.Echo.class,
                AwardPolicy.inactive(KeepersCallAdapter.ACTIVITY_ID, "mastery.listening"));
        r.register(new DawnChorusAdapter(mode), DawnChorusAdapter.Census.class,
                AwardPolicy.inactive(DawnChorusAdapter.ACTIVITY_ID, "mastery.listening"));
        r.register(new FrogPondAdapter(mode), FrogPondAdapter.Wetland.class,
                AwardPolicy.inactive(FrogPondAdapter.ACTIVITY_ID, "mastery.listening"));
        return r;
    }

    /** Registers an adapter for its result type; one adapter per activity id. */
    public <R> void register(ActivityResultAdapter<R> adapter, Class<R> resultType, AwardPolicy policy) {
        synchronized (lock) {
            String id = adapter.definition().activityId();
            if (!policy.activityId().equals(id)) throw new IllegalArgumentException("policy is for " + policy.activityId());
            if (entries.containsKey(id)) throw new IllegalArgumentException("adapter already registered: " + id);
            entries.put(id, new Entry(adapter, Objects.requireNonNull(resultType, "resultType"), policy));
        }
    }

    /** Replaces an activity's policy (an owner-approved revision); already-credited events are not paid again. */
    public void setPolicy(AwardPolicy policy) {
        synchronized (lock) {
            Entry e = entry(policy.activityId());
            entries.put(policy.activityId(), new Entry(e.adapter(), e.resultType(), policy));
        }
    }

    /** Issues the receipt for a finished game without settling it. */
    public ActivityResultReceipt receipt(String activityId, ActivityResultAdapter.Session session,
                                                      Object result) {
        synchronized (lock) {
            Entry e = entry(activityId);
            if (!e.resultType().isInstance(result))
                throw new IllegalArgumentException(activityId + " expects " + e.resultType().getSimpleName());
            return issue(e.adapter(), session, result);
        }
    }

    /** Issues the receipt and settles it once; returns the participants' awards. */
    public List<ProgressionLedger.Award> settle(String activityId, ActivityResultAdapter.Session session,
                                                             Object result) {
        synchronized (lock) {
            ActivityResultReceipt r = receipt(activityId, session, result);
            return record(r, entry(activityId).policy());
        }
    }

    /**
     * Credits an already-issued receipt (read from a journal or the wire) under the activity's current policy. The
     * receipt must be for a registered activity at the adapter's definition revision and mode (contest G49).
     */
    public List<ProgressionLedger.Award> credit(ActivityResultReceipt r) {
        synchronized (lock) {
            Entry e = entry(r.activityId());
            com.daedalus.world.activity.ActivityDefinition d = e.adapter().definition();
            if (r.definitionRevision() != d.revision() || r.mode() != d.mode())
                throw new IllegalArgumentException("receipt " + r.sourceKey() + " is for revision "
                        + r.definitionRevision() + " " + r.mode() + ", router has " + d.revision() + " " + d.mode());
            return record(r, e.policy());
        }
    }

    /** Every settled or credited receipt as journal lines, oldest first; each source key appears once. */
    public List<String> journal() {
        synchronized (lock) { return List.copyOf(journal); }
    }

    /**
     * Rebuilds progression from journal lines after a restart. Every line is checked first (all or nothing: a tampered
     * line credits nothing); then each receipt is credited exactly once. Returns how many receipts were new.
     */
    public int replay(List<String> lines) {
        List<ActivityResultReceipt> receipts = com.daedalus.world.activity.ReceiptJournal.readAll(lines);
        synchronized (lock) {
            int before = journal.size();
            for (ActivityResultReceipt r : receipts) credit(r);
            return journal.size() - before;
        }
    }

    private List<ProgressionLedger.Award> record(ActivityResultReceipt r, AwardPolicy policy) {
        synchronized (lock) {
            String prev = journalled.get(r.sourceKey());
            if (prev != null && !prev.equals(r.digest()))
                throw new ProgressionLedger.ConflictException("receipt " + r.sourceKey()
                        + " was already journalled with a different digest");
            List<ProgressionLedger.Award> awards = ledger.credit(r, policy);
            if (prev == null) {
                journalled.put(r.sourceKey(), r.digest());
                journal.add(com.daedalus.world.activity.ReceiptJournal.line(r));
            }
            return awards;
        }
    }

    public List<String> activities() {
        synchronized (lock) { return List.copyOf(entries.keySet()); }
    }

    private Entry entry(String id) {
        synchronized (lock) {
            Entry e = entries.get(id);
            if (e == null) throw new IllegalArgumentException("no adapter for " + id);
            return e;
        }
    }

    @SuppressWarnings("unchecked")
    private static <R> ActivityResultReceipt issue(ActivityResultAdapter<R> a, ActivityResultAdapter.Session s, Object r) {
        return a.toReceipt(s, (R) r);
    }
}
