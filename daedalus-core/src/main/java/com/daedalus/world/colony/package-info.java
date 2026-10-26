// SPDX-License-Identifier: MIT

/**
 * Colony Ledger day book (WZ14) for the Java server, contest gap G15 (youtube-master, Oct 2026).
 *
 * <ul>
 *   <li>{@link com.daedalus.world.colony.PyRandom}: CPython {@code random.Random} bit-for-bit, reusable by any Java
 *       port of a seeded Python core in {@code tools/}.</li>
 *   <li>{@link com.daedalus.world.colony.DayBook}: daily finds (fish by season and hour, bugs by seral stage,
 *       fossils or starmetal shards, ripe fruit), the museum collection, and news-board requests, the same draws as
 *       {@code tools/economy/colony_ledger.py}.</li>
 *   <li>{@link com.daedalus.world.colony.QuestProgress}: Java twin of the PORT09 ordered quest core
 *       ({@code DaedalusPortalQuestCore.h}).</li>
 *   <li>{@link com.daedalus.world.colony.QuestBoard}: binds requests to quests: deliver to the giver, then the
 *       population plan's story steps; every fill counts once.</li>
 * </ul>
 *
 * <p>Parity: {@code tools/economy/daybook_parity.py} writes {@code daybook-parity.tsv} from the Python cores;
 * {@code DayBookParityTest} and {@code PyRandomTest} replay it, and {@code test_daybook_parity.py} fails if it is stale.
 */
package com.daedalus.world.colony;
