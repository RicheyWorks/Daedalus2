// SPDX-License-Identifier: MIT

/**
 * Harbour pilot minigames. G586 Fog Channel Pilot ({@link com.daedalus.world.pilot.FogChannelPilot}) tracks a ship
 * through fog from one echo per foghorn blast: Viterbi over integer costs against the trust-each-echo habit. Seeds are
 * strings drawn through {@link com.daedalus.world.pilot.PyStringRandom}, which reproduces CPython's
 * {@code random.Random(str)}, so the same seed builds the same harbour in Python, Java and the header-only C++17
 * port (engines/unreal/.../DaedalusPilotFogChannelCore.h, parity data in core-test/pilot_fog_channel_parity.txt).
 */
package com.daedalus.world.pilot;
