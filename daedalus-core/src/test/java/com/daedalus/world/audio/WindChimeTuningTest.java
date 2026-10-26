// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class WindChimeTuningTest {
    @Test void everySetIsSolvableByTrimmingOnly() {
        for (long s = 0; s < 200; s++) {
            WindChimeTuning w = WindChimeTuning.seeded(s);
            List<Double> l = w.lengths();
            for (int i = 1; i < l.size(); i++) {
                assertThat(l.get(i)).isLessThanOrEqualTo(l.get(i - 1));
            }
            WindChimeTuning.Verdict v = w.judge(w.solution());
            assertThat(v.tuned()).as("seed %d", s).isTrue();
            assertThat(v.trimMm()).isGreaterThanOrEqualTo(0);
            assertThat(v.reason()).isEqualTo("tuned");
        }
    }

    @Test void rootIsTheLowestReachable() {
        for (long s = 0; s < 100; s++) {
            WindChimeTuning w = WindChimeTuning.seeded(s);
            boolean someTubeTooHigh = false;
            for (int i = 0; i < WindChimeTuning.TUBES; i++) {
                double lower = WindChimeTuning.hzOf(w.root() - 1 + WindChimeTuning.PENTATONIC.get(i));
                someTubeTooHigh |= WindChimeTuning.frequency(w.lengths().get(i)) > lower + 1e-9;
            }
            assertThat(someTubeTooHigh).as("seed %d", s).isTrue();
        }
    }

    @Test void physicsAndJudging() {
        assertThat(WindChimeTuning.frequency(450)).isCloseTo(196.0, within(1e-9));
        assertThat(WindChimeTuning.frequency(225)).isCloseTo(784.0, within(1e-9));
        assertThat(WindChimeTuning.lengthFor(196.0)).isCloseTo(450.0, within(1e-9));
        assertThat(WindChimeTuning.hzOf(69)).isEqualTo(440.0);
        assertThatThrownBy(() -> WindChimeTuning.frequency(0)).isInstanceOf(IllegalArgumentException.class);

        WindChimeTuning w = WindChimeTuning.seeded(5);
        assertThat(w.seed()).isEqualTo(5);
        assertThat(w.judge(null).tuned()).isFalse();
        assertThat(w.judge(List.of(1.0)).reason()).contains("need 5");
        List<Double> grown = new ArrayList<>(w.solution());
        grown.set(0, w.lengths().get(0) + 1);
        assertThat(w.judge(grown).reason()).contains("cannot grow");
        List<Double> off = new ArrayList<>(w.solution());
        off.set(2, off.get(2) * 0.99);
        WindChimeTuning.Verdict v = w.judge(off);
        assertThat(v.tuned()).isFalse();
        assertThat(v.reason()).startsWith("tube 2 off by");
        assertThat(v.tubes().get(2).cents()).isCloseTo(1200 * Math.log(1 / 0.9801) / Math.log(2), within(1e-6));
        assertThat(w.judge(w.lengths()).tuned()).isFalse();
    }
}