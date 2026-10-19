// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.labyrinth.EchoBellGate;
import com.daedalus.world.labyrinth.EchoSonar;
import java.util.ArrayList;
import java.util.List;
import java.util.function.LongFunction;
import org.junit.jupiter.api.Test;

/** Sweeps 300 seeds of every landed audio piece; every fundamental must obey {@link EarRule}. */
class EarRuleSweepTest {
    private static final int SEEDS = 300;

    private static void sweep(String piece, LongFunction<List<Double>> hz) {
        for (long s = 0; s < SEEDS; s++) {
            for (double f : hz.apply(s)) {
                assertThat(EarRule.ok(f)).as("%s seed %d: %.3f Hz", piece, s, f).isTrue();
            }
        }
    }

    @Test void helper() {
        assertThat(EarRule.ok(799.9)).isTrue();
        assertThat(EarRule.ok(800)).isFalse();
        assertThat(EarRule.ok(0)).isFalse();
        assertThat(EarRule.check(220, "a")).isEqualTo(220);
        assertThatThrownBy(() -> EarRule.check(1200, "whistle")).hasMessageContaining("whistle");
    }

    @Test void echoBellAndEchoSonar() {
        sweep("EchoBell", s -> {
            List<Double> out = new ArrayList<>();
            for (int d = 0; d <= 3; d++) {
                EchoBellGate.seeded(s, d, (s & 1) == 0).rings().forEach(r -> out.add(r.hz()));
            }
            return out;
        });
        sweep("G31 EchoSonar", s -> {
            EchoSonar e = EchoSonar.seeded(6 + (int) (s % 7), 6 + (int) (s % 5), s);
            return e.ping(e.start()).stream().map(EchoSonar.Echo::hz).toList();
        });
    }

    @Test void herbPieces() {
        sweep("G40 HerbChordGarden", s -> {
            HerbChordGarden g = HerbChordGarden.seeded(s);
            List<Double> out = new ArrayList<>();
            g.judge(g.solution()).detail().forEach(l -> out.addAll(l.playHz()));
            return out;
        });
        sweep("G81 CanonHerbCadence", s -> {
            CanonHerbCadence c = CanonHerbCadence.seeded(s);
            List<Double> out = new ArrayList<>();
            for (List<Integer> b : c.solutions().get(0)) {
                List<Herb> herbs = new ArrayList<>();
                b.forEach(i -> herbs.add(new Herb(c.hand().get(i), 1)));
                out.addAll(HerbChord.sound(herbs).frequencies());
            }
            return out;
        });
    }

    @Test void bellAndIslandPieces() {
        sweep("G52 FogBellCallSigns", s -> List.of(FogBellCallSigns.BELL_HZ));
        sweep("G60 WindChimeTuning", s -> {
            WindChimeTuning w = WindChimeTuning.seeded(s);
            List<Double> out = new ArrayList<>();
            for (int i = 0; i < WindChimeTuning.TUBES; i++) {
                out.add(w.targetHz(i));
                out.add(WindChimeTuning.frequency(w.lengths().get(i)));
            }
            return out;
        });
        sweep("G64 DripCaveChorus", s -> DripCaveChorus.seeded(s).drips().stream().map(DripCaveChorus.Drip::hz).toList());
        sweep("G72 BuoyBellHarbour", s -> BuoyBellHarbour.seeded(s).buoys().stream().map(BuoyBellHarbour.Buoy::hz).toList());
        sweep("G96 DopplerFlyby", s -> {
            DopplerFlyby d = DopplerFlyby.seeded(s);
            List<Double> out = new ArrayList<>(d.roster().stream().map(DopplerFlyby.Ark::hornHz).toList());
            out.add(d.heardApproach());
            out.add(d.heardRecede());
            return out;
        });
        sweep("G101 HullKnockSurvey", s -> HullKnockSurvey.seeded(s).plates().stream().map(HullKnockSurvey.Plate::heardHz).toList());
        sweep("G109 WaveOrgan", s -> WaveOrgan.seeded(s).pile().stream().map(WaveOrgan::frequency).toList());
        sweep("G114 JugBand", s -> {
            JugBand b = JugBand.seeded(s);
            List<Double> out = new ArrayList<>();
            List<Double> fill = b.solution();
            for (int i = 0; i < JugBand.JUGS; i++) {
                out.add(JugBand.frequency(b.jugs().get(i), 0));
                out.add(JugBand.frequency(b.jugs().get(i), fill.get(i)));
            }
            return out;
        });
        sweep("G121 KeepersCall", s -> KeepersCall.seeded(s).call(KeepersCall.MAX_LENGTH).stream().map(KeepersCall.Stroke::hz).toList());
        sweep("G124 DawnChorusCensus", s -> DawnChorusCensus.seeded(s).soundscape().stream().map(DawnChorusCensus.Call::hz).toList());
        sweep("G130 FrogPondNiches", s -> {
            List<Double> out = new ArrayList<>();
            for (FrogPondNiches.Frog f : FrogPondNiches.seeded(s).frogs()) {
                out.add(f.hz() * (1 + FrogPondNiches.BAND));
            }
            return out;
        });
        sweep("G135 BroodCycles", s -> List.of(BroodCycles.chorusHz()));
        sweep("G138 DrumRollId", s -> List.of(DrumRollId.knockHz()));
        sweep("G145 BuzzGarden", s -> BuzzGarden.seeded(s).bees().stream().map(BuzzGarden.Bee::hz).toList());
        sweep("G150 OwlFix", s -> List.of(OwlFix.seeded(s).hootHz()));
        sweep("G159 CricketThermometer", s -> CricketThermometer.seeded(s).soundscape().stream().map(CricketThermometer.Chirp::hz).toList());
        // G89 ThunderTowers emits unpitched thunder (delays only), nothing to sweep.
    }
}