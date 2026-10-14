// SPDX-License-Identifier: MIT
package com.daedalus.world.land;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Immutable physical placement ledger. Host-only data, never wallet or NFT authorization. */
public record RealmLayout(String realm, long revision, Set<Integer> reservedCells, List<Estate> estates) {
    public static final Set<String> REALMS = Set.of("WORLD-ZERO", "GALLERY-CITY", "PARCELS", "BRICKS",
            "LABYRINTH", "OCEAN", "PORTAL");

    /** Identity stays fixed when an estate moves; current x/y can differ from its original spiral address. */
    public record Estate(int landNumber, int x, int y, int size, long seed) {
        public Estate {
            if (!LandGrid.valid(landNumber) || LandGrid.estate(x, y, size) < 0) {
                throw new IllegalArgumentException("Invalid estate identity or footprint");
            }
        }
        public int district() { return LandGrid.districtOfCell(x, y); }
    }

    public RealmLayout {
        requireRealm(realm);
        if (revision < 0) throw new IllegalArgumentException("Negative layout revision");
        if (reservedCells.size() > LandGrid.COUNT || estates.size() > LandGrid.COUNT) {
            throw new IllegalArgumentException("Layout exceeds grid capacity");
        }
        reservedCells = Set.copyOf(reservedCells);
        estates = List.copyOf(estates.stream().sorted(Comparator.comparingInt(Estate::landNumber)).toList());
        Set<Integer> occupied = new HashSet<>();
        for (int number : reservedCells) {
            if (!LandGrid.valid(number)) throw new IllegalArgumentException("Invalid reserved cell");
            occupied.add(number);
        }
        Set<Integer> ids = new HashSet<>();
        for (Estate e : estates) {
            if (!ids.add(e.landNumber())) throw new IllegalArgumentException("Duplicate estate identity");
            for (int y = e.y(); y < e.y() + e.size(); y++) {
                for (int x = e.x(); x < e.x() + e.size(); x++) {
                    if (!occupied.add(LandGrid.number(x, y))) {
                        throw new IllegalArgumentException("Estate overlaps another footprint or reserved cell");
                    }
                }
            }
        }
    }

    public static void requireRealm(String realm) {
        if (realm == null || !REALMS.contains(realm)) throw new IllegalArgumentException("Unknown canonical realm");
    }

    public static RealmLayout empty(String realm, Set<Integer> reserved) {
        return new RealmLayout(realm, 0, reserved, List.of());
    }

    /** Initial identity is the lowest covered cell. Existing identities cannot be reallocated by place(). */
    public RealmLayout place(int x, int y, int size, long seed) {
        int number = LandGrid.estate(x, y, size);
        Estate e = new Estate(number, x, y, size, seed);
        List<Estate> next = new ArrayList<>(estates);
        next.add(e);
        return new RealmLayout(realm, Math.incrementExact(revision), reservedCells, next);
    }

    /** Host validates authority separately; optimistic revision checking happens in RealmLayoutStore. */
    public RealmLayout move(int landNumber, int x, int y) {
        List<Estate> next = new ArrayList<>(estates.size());
        boolean found = false;
        for (Estate e : estates) {
            if (e.landNumber() == landNumber) {
                next.add(new Estate(landNumber, x, y, e.size(), e.seed()));
                found = true;
            } else next.add(e);
        }
        if (!found) throw new IllegalArgumentException("Unknown estate identity");
        return new RealmLayout(realm, Math.incrementExact(revision), reservedCells, next);
    }

    public List<Estate> district(int district) {
        if (district < 0 || district >= 100) throw new IllegalArgumentException("District must be 0..99");
        return estates.stream().filter(e -> e.district() == district).toList();
    }
}
