// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

class ExploreInputTest {

    @Test
    void wasdAndAStickAreTheSameIntent() {
        ExploreInput.Intent keys = ExploreInput.keyboard(true, false, false, false);
        ExploreInput.Intent stick = ExploreInput.gamepad(0, -1, 0, 0, false, false);
        assertThat(keys.forward()).isCloseTo(1.0, within(0.001));
        assertThat(stick.forward()).isCloseTo(1.0, within(0.001));
        assertThat(keys.strafe()).isZero();
        assertThat(stick.strafe()).isZero();
    }

    @Test
    void aDeadzoneDropsNoise() {
        assertThat(ExploreInput.dead(0.05)).isZero();
        assertThat(ExploreInput.dead(-0.05)).isZero();
        assertThat(ExploreInput.dead(1.0)).isCloseTo(1.0, within(0.001));
    }

    @Test
    void glfwStickUpWalksLookAndLookScalesWithDt() {
        ExploreInput.Intent back = ExploreInput.gamepad(0, 1, 0, 0, false, false);
        assertThat(back.forward()).isCloseTo(-1.0, within(0.001));
        ExploreInput.Intent look = ExploreInput.gamepad(0, 0, 1, -1, false, false, 0.05);
        assertThat(look.yawDelta()).isCloseTo(ExploreInput.STICK_LOOK * 0.05, within(0.0001));
        assertThat(look.pitchDelta()).isCloseTo(ExploreInput.STICK_LOOK * 0.05, within(0.0001));
        assertThat(ExploreInput.gamepad(0, 0, 1, 0, false, false).yawDelta()).isZero();
    }

    @Test
    void snapTurnIsFortyFiveDegrees() {
        ExploreInput.Intent snap = ExploreInput.gamepad(0, 0, 0, 0, false, true);
        assertThat(snap.yawDelta()).isEqualTo(ExploreInput.SNAP_TURN);
        ExploreInput.Intent left = ExploreInput.gamepad(0, 0, 0, 0, true, false);
        assertThat(left.yawDelta()).isEqualTo(-ExploreInput.SNAP_TURN);
    }

    @Test
    void mouseLookTurnsTheBody() {
        ExploreBody body = new ExploreBody(0, 0, 0, 0);
        ExploreInput.applyLook(body, ExploreInput.mouse(100, 0));
        assertThat(body.yaw()).isLessThan(0);
        ExploreInput.applyLook(body, new ExploreInput.Intent(0, 0, 0, 10));
        assertThat(body.pitch()).isEqualTo(ExploreBody.PITCH_LIMIT);
    }

    @Test
    void yawZeroWalksNorthAsMinusZ() {
        ExploreBody body = new ExploreBody(0, 0, 0, 0);
        double[] move = ExploreInput.moveVector(body, new ExploreInput.Intent(1, 0, 0, 0), 1);
        assertThat(move[0]).isCloseTo(0, within(0.001));
        assertThat(move[1]).isCloseTo(-1, within(0.001));
    }

    @Test
    void diagonalKeysNormalize() {
        ExploreInput.Intent diag = ExploreInput.keyboard(true, false, false, true);
        assertThat(Math.hypot(diag.forward(), diag.strafe())).isCloseTo(1.0, within(0.001));
    }
}
