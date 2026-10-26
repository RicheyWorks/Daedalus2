// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.activity.ReceiptJournal;
import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.cellar.Preserve;
import com.daedalus.world.brew.cellar.Preserve.Method;
import com.daedalus.world.brew.cellar.RootCellar;
import com.daedalus.world.brew.concert.GraduationConcert;
import com.daedalus.world.brew.letters.Destination;
import com.daedalus.world.brew.letters.LettersByArk;
import com.daedalus.world.brew.round.HarbourRound;
import com.daedalus.world.brew.school.Pupil;
import com.daedalus.world.brew.school.SongSchool;
import com.daedalus.world.colony.PlotState;
import com.daedalus.world.odds.weather.Sky;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Contest G153: receipts hub XII over youtube-master's story chapters 10-13, driven by the real cores. */
class HubTwelveAdaptersTest {

    static final ActivityParticipant WREN =
            new ActivityParticipant("life:green-wren-1", ActivityParticipant.Kind.LIFE, "bird", "singing");
    static final ActivityParticipant GOAT =
            new ActivityParticipant("life:post-goat-2", ActivityParticipant.Kind.LIFE, "animal", "companionship");

    List<FoundTune> tunes;

    @BeforeEach
    void setUp() throws Exception {
        try (var in = getClass().getResourceAsStream("/com/daedalus/world/brew/found_tunes.csv")) {
            tunes = FoundTune.parseCsv(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        }
    }

    static ActivityResultAdapter.Session session(String id, ActivityParticipant p) {
        return new ActivityResultAdapter.Session("sess-" + id, "res-" + id, "contest-host", "verify:" + id,
                List.of(p), List.of("evt:" + id), 1_760_880_000_000L);
    }

    static int jar(RootCellar c, PlotState plot, String item, Method m, String ev) {
        plot.add(item, 1);
        Preserve.cost(m).forEach((k, v) -> plot.add(k, v));
        assertThat(c.preserve(ev, item, m, plot)).isEqualTo(RootCellar.Outcome.STORED);
        return c.jars().get(c.jars().size() - 1).id();
    }

    /** Old Wick's plan: review what's due, then start new songs with the lessons left. */
    static void teachADay(SongSchool s) {
        int n = 0;
        for (SongSchool.Card c : s.dueToday()) {
            if (s.lessonsLeft() == 0) {
                break;
            }
            s.review("d" + s.day() + "r" + n++, c.pupil(), c.song());
        }
        for (Pupil p : s.pupils()) {
            for (String song : s.songsFor(p.id())) {
                if (s.lessonsLeft() > 0 && s.card(p.id(), song) == null) {
                    s.introduce("d" + s.day() + "i" + n++, p.id(), song);
                }
            }
        }
        s.nextDay();
    }

    SongSchool school(long seed) {
        return new SongSchool(SongSchool.thirteenSongs(tunes), SongSchool.fromFarIslands(Destination.island(), seed),
                seed);
    }

    @Test
    void lettersByArkFinishedChapterCompletesInPlayRefused() {
        LettersByArkAdapter a = new LettersByArkAdapter(ActivityMode.AUTHORITATIVE);
        PlotState plot = new PlotState();
        RootCellar c = new RootCellar(9, 50);
        LettersByArk x = new LettersByArk(c, Destination.island(), Sky.SQUALL, 13);
        assertThatThrownBy(() -> LettersByArkAdapter.Post.of(x, false)).hasMessageContaining("in progress");
        x.ship("k", jar(c, plot, "fish", Method.SALT, "j1"), "kelp_harbour", false, plot);
        x.ship("c", jar(c, plot, "Bacon", Method.SMOKE, "j2"), "cinder_reach", false, plot);
        x.ship("g", jar(c, plot, "Egg", Method.PICKLE, "j3"), "glass_shoals", false, plot);
        x.ship("o", jar(c, plot, "Moonbean", Method.DRY, "j4"), "far_orchard", false, plot);
        var gone = a.toReceipt(session("lb-a", GOAT), LettersByArkAdapter.Post.of(x, true));
        assertThat(gone.outcome()).isEqualTo(ActivityOutcome.ABANDONED);
        assertThat(gone.measures()).containsEntry("steps", 1L);
        int guard = 0;
        while (x.quest().stepIndex() < 3 && guard++ < 60) {
            x.nextDay(plot);
        }
        x.talk("dov");
        assertThat(x.quest().complete()).isTrue();
        var done = a.toReceipt(session("lb-1", GOAT), LettersByArkAdapter.Post.of(x, false));
        assertThat(done.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(done.measures().get("landed_good")).isGreaterThanOrEqualTo(3L);
        assertThat(done.measures().get("replies")).isGreaterThanOrEqualTo(2L);
        assertThatThrownBy(() -> new LettersByArkAdapter.Post(true, 2, 0, 0, false)).hasMessageContaining("every step");
    }

    @Test
    void songSchoolGraduatingThreeCompletesEarlyTermRefused() {
        SongSchoolAdapter a = new SongSchoolAdapter(ActivityMode.AUTHORITATIVE);
        for (long seed = 0; seed < 5; seed++) {
            SongSchool s = school(seed);
            teachADay(s);
            assertThatThrownBy(() -> SongSchoolAdapter.Term.of(s, false)).hasMessageContaining("in progress");
            assertThat(a.toReceipt(session("ss-a" + seed, WREN), SongSchoolAdapter.Term.of(s, true)).outcome())
                    .isEqualTo(ActivityOutcome.ABANDONED);
            int guard = 0;
            while (s.graduates().size() < SongSchool.GRADUATES_NEEDED && guard++ < 200) {
                teachADay(s);
            }
            var r = a.toReceipt(session("ss-" + seed, WREN), SongSchoolAdapter.Term.of(s, false));
            assertThat(r.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
            assertThat(r.measures().get("graduates")).isGreaterThanOrEqualTo((long) SongSchool.GRADUATES_NEEDED);
            assertThat(r.measures().get("days")).isGreaterThanOrEqualTo(16L);
        }
        assertThat(a.toReceipt(session("ss-x", WREN), new SongSchoolAdapter.Term(1, 9, false)).outcome())
                .isEqualTo(ActivityOutcome.FAILED);
    }

    @Test
    void graduationConcertCheeredCompletesRoughFails() {
        GraduationConcertAdapter a = new GraduationConcertAdapter(ActivityMode.AUTHORITATIVE);
        SongSchool s = school(3);
        int guard = 0;
        while (s.graduates().size() < SongSchool.GRADUATES_NEEDED && guard++ < 200) {
            teachADay(s);
        }
        GraduationConcert c = GraduationConcert.fromSchool(s, tunes, 0);
        assertThatThrownBy(() -> GraduationConcertAdapter.Evening.of(c, false)).hasMessageContaining("under way");
        int n = 0;
        for (GraduationConcert.Slot slot : c.bestSet().subList(0, GraduationConcert.SOLOS)) {
            assertThat(c.perform("b" + n++, slot.singer(), slot.song())).isEqualTo(GraduationConcert.Outcome.SUNG);
        }
        assertThat(c.close("close")).isEqualTo(GraduationConcert.Outcome.CHEERED);
        var r = a.toReceipt(session("gc-1", WREN), GraduationConcertAdapter.Evening.of(c, false));
        assertThat(r.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(r.measures()).containsEntry("key_changes", (long) c.best()).containsEntry("evenings", 1L);
        var rough = new GraduationConcertAdapter.Evening(false, c.best() + GraduationConcert.SLACK + 1, c.best(), 1,
                false);
        assertThat(a.toReceipt(session("gc-2", WREN), rough).outcome()).isEqualTo(ActivityOutcome.FAILED);
        assertThatThrownBy(() -> new GraduationConcertAdapter.Evening(true, c.best() + GraduationConcert.SLACK + 1,
                c.best(), 1, false)).hasMessageContaining("slack");
    }

    @Test
    void harbourRoundSweetAtTheHarbourCompletesRehearsalsRefused() {
        HarbourRoundAdapter a = new HarbourRoundAdapter(ActivityMode.AUTHORITATIVE);
        Map<String, List<Integer>> notes = HarbourRound.notesOf(tunes);
        String alpine = "Item_YTM_Record_Alpine";
        HarbourRound r = new HarbourRound(notes, Set.of(alpine));
        for (int i = 1; i <= HarbourRound.REHEARSALS; i++) {
            r.rehearse("r" + i, alpine, r.best(alpine, 2).entries());
        }
        assertThatThrownBy(() -> HarbourRoundAdapter.Harbour.of(r, false)).hasMessageContaining("in progress");
        assertThat(r.sing("s1", alpine, r.best(alpine, HarbourRound.HARBOUR_VOICES).entries()))
                .isEqualTo(HarbourRound.Outcome.SWEET);
        var done = a.toReceipt(session("hr-1", WREN), HarbourRoundAdapter.Harbour.of(r, false));
        assertThat(done.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(done.measures()).containsEntry("sweet", 1L);
        assertThat(done.measures().get("harmony_pct")).isGreaterThanOrEqualTo(75L);
        assertThat(a.toReceipt(session("hr-2", WREN), new HarbourRoundAdapter.Harbour(false, 40, false)).outcome())
                .isEqualTo(ActivityOutcome.FAILED);
        assertThatThrownBy(() -> new HarbourRoundAdapter.Harbour(true, 101, false)).hasMessageContaining("harmony");
    }

    @Test
    void contestAllRoutesHubTwelveSettlesOnceAndReplays() {
        ActivityRouter r = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        assertThat(r.activities()).contains(LettersByArkAdapter.ACTIVITY_ID, SongSchoolAdapter.ACTIVITY_ID,
                GraduationConcertAdapter.ACTIVITY_ID, HarbourRoundAdapter.ACTIVITY_ID);
        AwardPolicy policy = new AwardPolicy(HarbourRoundAdapter.ACTIVITY_ID, 1, "mastery.island-story",
                Map.of("sweet", 1L), 60);
        r.setPolicy(policy);
        HarbourRoundAdapter.Harbour h = new HarbourRoundAdapter.Harbour(true, 100, false);
        r.settle(HarbourRoundAdapter.ACTIVITY_ID, session("route-hr", WREN), h);
        r.settle(HarbourRoundAdapter.ACTIVITY_ID, session("route-hr", WREN), h);
        long once = r.total("life:green-wren-1", "mastery.island-story");
        assertThat(once).isPositive();
        assertThat(ReceiptJournal.readAll(r.journal())).hasSize(1);
        ActivityRouter restarted = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        restarted.setPolicy(policy);
        assertThat(restarted.replay(r.journal())).isEqualTo(1);
        assertThat(restarted.total("life:green-wren-1", "mastery.island-story")).isEqualTo(once);
        assertThatThrownBy(() -> r.settle(SongSchoolAdapter.ACTIVITY_ID, session("route-x", WREN), h))
                .hasMessageContaining("expects");
    }
}