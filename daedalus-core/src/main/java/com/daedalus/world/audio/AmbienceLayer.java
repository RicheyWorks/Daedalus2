package com.daedalus.world.audio;

/**
 * One looping bed in an ambience mix.
 *
 * @param id stable layer id (asset key, e.g. "wind", "birds_day")
 * @param gain linear gain 0..1 after mix normalisation
 * @param lowpassHz lowpass cutoff (distance/weather muffling)
 * @param density event rate 0..1 for one-shot layers (birdsong, drips)
 */
public record AmbienceLayer(String id, double gain, double lowpassHz, double density) {
}
