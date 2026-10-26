// SPDX-License-Identifier: MIT

/**
 * Melody Brewing (Youtube Master Island, contest gap G25, youtube-master): the ordered-herb brew bench.
 *
 * <ul>
 *   <li>{@link com.daedalus.world.brew.MelodyBrew}: the rule set, an exact port of
 *       {@code engines/unreal/ytm-island/herbcombo.py} (parity fixture {@code melody-parity.tsv}).</li>
 *   <li>{@link com.daedalus.world.brew.BrewBench}: spends herbs from a {@link com.daedalus.world.colony.PlotState},
 *       learns found tunes from seed-song records, purifies raw water on a cadence; every brew counts once.</li>
 *   <li>{@link com.daedalus.world.brew.FoundTune}: rows of {@code found_tunes.csv}.</li>
 *   <li>{@link com.daedalus.world.brew.PitchTable}: herb to pitch class, shared with prometheus's HerbChord.</li>
 * </ul>
 * Story beats and the test behind each: {@code STORY.md} in this folder. Split with Harmonic Herbs:
 * {@code engines/unreal/ytm-island/BREW_SPLIT.md} (agreed).
 */
package com.daedalus.world.brew;
