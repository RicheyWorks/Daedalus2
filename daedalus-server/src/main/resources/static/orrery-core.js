// SPDX-License-Identifier: MIT
// The Orrery Reach's herbs for the browser (ADR-057): a port of DaedalusOrreryCore.h. tools/reach_parity.mjs checks
// it against engines/unreal/core-test/orrery_parity.txt (the table and all 576 brews, written by the C++ test).
export const HERBS = [
  ["Dawnthistle", 6, "Keeper"], ["Midnightmint", 0, "Keeper"],
  ["Sunsprig", 8, "Lantern"], ["Duskmallow", 18, "Lantern"],
  ["Orbitfern", 9, "Ark"], ["Moonvetch", 21, "Ark"],
  ["Eclipsebell", 13, "Shard"], ["Meteorsage", 1, "Shard"],
  ["Equinoxbalm", 10, "Wanderer"], ["Cometcress", 3, "Wanderer"],
  ["Heartstonebloom", 7, "Hearth"], ["Starsedge", 22, "Hearth"],
  ["Zenithclover", 11, "Spindle"], ["Nebulawort", 23, "Spindle"],
  ["Noonspire", 12, "Crown"], ["Polarisroot", 2, "Crown"],
  ["Driftfennel", 16, "Tide"], ["Nadirmoss", 4, "Tide"],
  ["Quasarthyme", 14, "Forge"], ["Twilightsorrel", 19, "Forge"],
  ["Solsticerue", 15, "Kite"], ["Auroraleaf", 5, "Kite"],
  ["Lunarlily", 17, "Loom"], ["Galaxygrass", 20, "Loom"],
].map(([name, hour, constellation]) => ({ name, hour, constellation }));

const ECLIPSES = ["Umbra", "Penumbra", "Corona", "Diamondring", "Baileybeads", "Totality", "Annular", "Hybrid"];

export const isDay = (hour) => hour >= 6 && hour < 18;
export const findHerb = (name) => HERBS.find((h) => h.name === name) || null;

/** Whole sky hour 0..23 for any hour value. */
export function wholeHour(hour) {
  if (!Number.isFinite(hour)) return 0;
  return ((Math.floor(hour) % 24) + 24) % 24;
}

/** The herb in bloom at this hour (exactly one, since there is one per hour). */
export const inBloom = (hour) => HERBS.find((h) => h.hour === wholeHour(hour));

/** "" when the two make nothing. */
export function brewOf(a, b) {
  const x = findHerb(a), y = findHerb(b);
  if (!x || !y || a === b) return "";
  if (x.constellation === y.constellation) return x.constellation + " Brew";
  if (isDay(x.hour) !== isDay(y.hour)) return "Eclipse Brew: " + ECLIPSES[(x.hour + y.hour) % 8];
  return "";
}
