// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.odds.insurance.UnderwriterQuest;
import com.daedalus.world.odds.launch.LaunchOption;
import com.daedalus.world.odds.launch.LaunchPlanner;
import com.daedalus.world.odds.launch.LaunchWindowQuest;
import com.daedalus.world.odds.ledger.KeepersLedgerQuest;
import com.daedalus.world.odds.rival.RivalBook;
import com.daedalus.world.odds.rival.RivalBookQuest;
import com.daedalus.world.odds.tote.ToteQuest;
import com.daedalus.world.odds.weather.Sky;
import com.daedalus.world.odds.weather.StormGlass;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Contest G95: receipts hub VII over the landed OddsReaper quests, driven by the real quest objects. */
class HubSevenAdaptersTest {

    static final ActivityParticipant RAVEN =
            new ActivityParticipant("life:tally-raven-1", ActivityParticipant.Kind.LIFE, "bird", "counting");
    static final ActivityParticipant GULL =
            new ActivityParticipant("life:glass-gull-2", ActivityParticipant.Kind.LIFE, "bird", "observation");
    static final ActivityParticipant HOUND =
            new ActivityParticipant("life:odds-hound-3", ActivityParticipant.Kind.LIFE, "animal", "scouting");

    static ActivityResultAdapter.Session session(String id, ActivityParticipant p) {
        return new ActivityResultAdapter.Session("sess-" + id, "res-" + id, "contest-host", "verify:" + id,
                List.of(p), List.of("evt:" + id), 1_760_872_000_000L);
    }

    @Test
    void keepersLedgerDoubledCompletesBrokeFailsOpenIsRefused() {
        KeepersLedgerAdapter a = new KeepersLedgerAdapter(ActivityMode.AUTHORITATIVE);
        KeepersLedgerQuest open = new KeepersLedgerQuest();
        assertThatThrownBy(() -> KeepersLedgerAdapter.Ledger.of(open, false)).hasMessageContaining("in progress");
        assertThat(a.toReceipt(session("kl-0", RAVEN), KeepersLedgerAdapter.Ledger.of(open, true)).outcome())
                .isEqualTo(ActivityOutcome.ABANDONED);

        KeepersLedgerQuest bold = new KeepersLedgerQuest();
        bold.wager("squall-cup", KeepersLedgerQuest.START, 0.5, 3.0, true);
        KeepersLedgerAdapter.Ledger doubled = KeepersLedgerAdapter.Ledger.of(bold, false);
        assertThat(doubled.doubled()).isTrue();
        assertThat(doubled.keepersMark()).as("over the advice: no Keeper's Mark").isFalse();
        assertThat(a.toReceipt(session("kl-1", RAVEN), doubled).measures())
                .containsEntry("doubled", 1L).containsEntry("balance", 60L).containsEntry("wagers", 1L);

        KeepersLedgerQuest rash = new KeepersLedgerQuest();
        rash.wager("parlay", KeepersLedgerQuest.START, 0.5, 2.0, false);
        assertThat(a.toReceipt(session("kl-2", RAVEN), KeepersLedgerAdapter.Ledger.of(rash, false)).outcome())
                .isEqualTo(ActivityOutcome.FAILED);
        assertThatThrownBy(() -> new KeepersLedgerAdapter.Ledger(false, true, 10, 1, 1, false))
                .hasMessageContaining("Mark");
    }

    @Test
    void launchWindowCreditsTheWiseChoiceNotTheSky() {
        LaunchPlanner p = LaunchPlanner.ODDSREAPER;
        LaunchWindowAdapter a = new LaunchWindowAdapter(ActivityMode.AUTHORITATIVE);
        LaunchWindowQuest wise = new LaunchWindowQuest(p, StormGlass.Reading.LOW);
        assertThatThrownBy(() -> LaunchWindowAdapter.Launch.of(wise, false)).hasMessageContaining("FORECAST");
        wise.choose(wise.best().route(), wise.best().day());
        wise.sail(68L);
        LaunchWindowAdapter.Launch good = LaunchWindowAdapter.Launch.of(wise, false);
        assertThat(good.wise()).isTrue();
        assertThat(good.expectedSouls()).isEqualTo(good.bestSouls());
        assertThat(a.toReceipt(session("lw-1", GULL), good).outcome()).isEqualTo(ActivityOutcome.COMPLETED);

        LaunchOption worst = p.options(StormGlass.Reading.LOW).stream()
                .min(java.util.Comparator.comparingDouble(LaunchOption::expectedLife)).orElseThrow();
        LaunchWindowQuest rash = new LaunchWindowQuest(p, StormGlass.Reading.LOW);
        rash.choose(worst.route(), worst.day());
        rash.sail(68L);
        LaunchWindowAdapter.Launch bad = LaunchWindowAdapter.Launch.of(rash, false);
        assertThat(bad.wise()).isFalse();
        assertThat(a.toReceipt(session("lw-2", GULL), bad).outcome()).isEqualTo(ActivityOutcome.FAILED);
    }

    @Test
    void rivalBookExposedCompletesFooledFails() {
        double[] fair = {0.5, 0.3, 0.2};
        RivalBookAdapter a = new RivalBookAdapter(ActivityMode.AUTHORITATIVE);
        RivalBookQuest sharp = new RivalBookQuest(fair, RivalBook.of(1 / fair[0] * 1.3, 1 / fair[1] * 0.8, 1 / fair[2] * 1.1));
        assertThat(sharp.valueLines()).isEqualTo(2);
        assertThatThrownBy(() -> RivalBookAdapter.Scan.of(sharp, false)).hasMessageContaining("SCANNING");
        sharp.call(0);
        sharp.call(2);
        RivalBookAdapter.Scan exposed = RivalBookAdapter.Scan.of(sharp, false);
        assertThat(a.toReceipt(session("rb-1", HOUND), exposed).measures())
                .containsEntry("exposed", 1L).containsEntry("found", 2L).containsEntry("reward", (long) RivalBookQuest.REWARD);

        RivalBookQuest fooled = new RivalBookQuest(fair, RivalBook.of(1 / fair[0] * 1.3, 1 / fair[1] * 0.8, 1 / fair[2] * 1.1));
        fooled.call(1);
        fooled.call(1);
        assertThat(a.toReceipt(session("rb-2", HOUND), RivalBookAdapter.Scan.of(fooled, false)).outcome())
                .isEqualTo(ActivityOutcome.FAILED);
    }

    @Test
    void arkUnderwriterSolventCompletesBustFailsQuotesAreRefused() {
        ArkUnderwriterAdapter a = new ArkUnderwriterAdapter(ActivityMode.AUTHORITATIVE);
        UnderwriterQuest quoting = new UnderwriterQuest(Sky.SQUALL, 2026);
        quoting.quote(0.40);
        assertThatThrownBy(() -> ArkUnderwriterAdapter.Season.of(quoting, false)).hasMessageContaining("REJECTED");
        boolean sawSolvent = false;
        boolean sawBust = false;
        for (long s = 1; s <= 400 && !(sawSolvent && sawBust); s++) {
            UnderwriterQuest q = new UnderwriterQuest(Sky.SQUALL, 2026);
            q.quote(UnderwriterQuest.FAIR_LOADING);
            UnderwriterQuest.Stage end = q.sail(s);
            ArkUnderwriterAdapter.Season season = ArkUnderwriterAdapter.Season.of(q, false);
            ActivityOutcome o = a.toReceipt(session("au-" + s, RAVEN), season).outcome();
            if (end == UnderwriterQuest.Stage.SOLVENT) {
                sawSolvent = true;
                assertThat(o).isEqualTo(ActivityOutcome.COMPLETED);
                assertThat(season.shortfallHerbs()).isZero();
            } else {
                sawBust = true;
                assertThat(o).isEqualTo(ActivityOutcome.FAILED);
            }
            assertThat(season.bustRiskPm()).isLessThanOrEqualTo((int) (UnderwriterQuest.MAX_INSOLVENCY * 1000));
        }
        assertThat(sawSolvent).isTrue();
    }

    @Test
    void keepersToteWonCompletesAndRecordsTheOverlay() {
        double[] cup = {0.5, 0.3, 0.2};
        KeepersToteAdapter a = new KeepersToteAdapter(ActivityMode.AUTHORITATIVE);
        ToteQuest open = new ToteQuest(cup, 3);
        assertThatThrownBy(() -> KeepersToteAdapter.Heat.of(open, false)).hasMessageContaining("BOARD_OPEN");
        boolean sawWin = false;
        boolean sawLoss = false;
        for (long race = 1; race <= 200 && !(sawWin && sawLoss); race++) {
            ToteQuest q = new ToteQuest(cup, 3);
            q.back(0, 5);
            q.race(race);
            KeepersToteAdapter.Heat h = KeepersToteAdapter.Heat.of(q, false);
            assertThat(h.pool()).isEqualTo(q.pool());
            ActivityOutcome o = a.toReceipt(session("kt-" + race, HOUND), h).outcome();
            if (q.stage() == ToteQuest.Stage.WON) {
                sawWin = true;
                assertThat(o).isEqualTo(ActivityOutcome.COMPLETED);
            } else {
                sawLoss = true;
                assertThat(o).isEqualTo(ActivityOutcome.FAILED);
            }
        }
        assertThat(sawWin && sawLoss).isTrue();
    }

    @Test
    void contestAllRoutesHubSevenSettlesOnceAndReplays() {
        ActivityRouter r = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        assertThat(r.activities()).contains(KeepersLedgerAdapter.ACTIVITY_ID, LaunchWindowAdapter.ACTIVITY_ID,
                RivalBookAdapter.ACTIVITY_ID, ArkUnderwriterAdapter.ACTIVITY_ID, KeepersToteAdapter.ACTIVITY_ID);
        AwardPolicy policy = new AwardPolicy(KeepersLedgerAdapter.ACTIVITY_ID, 1, "mastery.reckoning",
                Map.of("keepers_mark", 30L, "disciplined", 2L), 50);
        r.setPolicy(policy);
        KeepersLedgerAdapter.Ledger l = new KeepersLedgerAdapter.Ledger(true, true, 44, 5, 5, false);
        r.settle(KeepersLedgerAdapter.ACTIVITY_ID, session("route-kl", RAVEN), l);
        r.settle(KeepersLedgerAdapter.ACTIVITY_ID, session("route-kl", RAVEN), l);
        assertThat(r.total("life:tally-raven-1", "mastery.reckoning")).isEqualTo(40);
        assertThat(r.journal()).hasSize(1);

        ActivityRouter restarted = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        restarted.setPolicy(policy);
        assertThat(restarted.replay(r.journal())).isEqualTo(1);
        assertThat(restarted.total("life:tally-raven-1", "mastery.reckoning")).isEqualTo(40);
        assertThatThrownBy(() -> r.settle(KeepersToteAdapter.ACTIVITY_ID, session("route-x", HOUND), l))
                .hasMessageContaining("expects");
    }
}