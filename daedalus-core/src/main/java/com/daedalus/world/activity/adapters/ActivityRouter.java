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
            return ledger.credit(r, entry(activityId).policy());
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
