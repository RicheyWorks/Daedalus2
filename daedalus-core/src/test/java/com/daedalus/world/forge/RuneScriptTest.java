// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class RuneScriptTest {

    @Test
    void matchesJdk() {
        SplittableRandom r = new SplittableRandom(408);
        for (int t = 0; t < 400; t++) {
            byte[] d = new byte[r.nextInt(70)];
            r.nextBytes(d);
            String std = Base64.getEncoder().encodeToString(d);
            String url = Base64.getUrlEncoder().withoutPadding().encodeToString(d);
            assertThat(RuneScript.encode(d, false, true)).isEqualTo(std);
            assertThat(RuneScript.encode(d, true, false)).isEqualTo(url);
            assertThat(RuneScript.decode(std, false)).containsExactly(d);
            assertThat(RuneScript.decode(url, true)).containsExactly(d);
        }
    }

    @Test
    void rfcVectorsAndStrictness() {
        String[] in = {"", "f", "fo", "foo", "foob", "fooba", "foobar"};
        String[] out = {"", "Zg==", "Zm8=", "Zm9v", "Zm9vYg==", "Zm9vYmE=", "Zm9vYmFy"};
        for (int i = 0; i < in.length; i++) {
            byte[] b = in[i].getBytes(StandardCharsets.US_ASCII);
            assertThat(RuneScript.encode(b, false, true)).isEqualTo(out[i]);
            assertThat(RuneScript.decode(out[i], false)).containsExactly(b);
        }
        assertThatThrownBy(() -> RuneScript.decode("Zg=", false)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RuneScript.decode("Zh==", false)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RuneScript.decode("Z", false)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RuneScript.decode("Zm9v=Yg=", false)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RuneScript.decode("-_8", false)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RuneScript.decode("Zm9===", false)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void grades() {
        byte[] d = {1, 2, 3, 4};
        String s = RuneScript.encode(d, true, false);
        assertThat(RuneScript.grade(s, d, true)).isEqualTo(RuneScript.Grade.LEGIBLE);
        assertThat(RuneScript.grade(s + "!", d, true)).isEqualTo(RuneScript.Grade.MISCARVED);
        assertThat(RuneScript.forgemasterLine(RuneScript.Grade.LEGIBLE)).contains("Forgemaster");
        assertThat(RuneScript.forgemasterLine(RuneScript.Grade.MISCARVED)).contains("miscarved");
        assertThat(RuneScript.QUEST_ID).isEqualTo("q_rune_script");
    }
}
