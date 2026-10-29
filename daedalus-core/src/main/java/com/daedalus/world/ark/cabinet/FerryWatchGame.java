// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import com.daedalus.world.ark.FerryWatch;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/**
 * Cabinet adapter for G412 The Ferry Watch (one player). The safety rule is {@link FerryWatch#safe}; a finished
 * game is checked with {@link FerryWatch#valid}. The piece plans only from the start, so the cabinet's mid-game hint
 * is a small breadth-first search here over (crew near, raiders near, ferry side) using the piece's safety rule.
 * A move is the load {@code crew,raiders}.
 */
public final class FerryWatchGame implements ArkCabinetGame {

    private final int m;
    private final int c;
    private final int b;
    private int crewNear;
    private int raidersNear;
    private boolean ferryNear = true;
    private final List<int[]> loads = new ArrayList<>();

    /** Three crew, three raiders, a two-seat ferry. */
    public FerryWatchGame() {
        this(3, 3, 2);
    }

    /** m crew, c raiders, ferry of b seats. */
    public FerryWatchGame(int m, int c, int b) {
        if (m < 0 || c < 0 || b < 1 || m + c > FerryWatch.MAX_PEOPLE) {
            throw new IllegalArgumentException("bad crossing");
        }
        this.m = m;
        this.c = c;
        this.b = b;
        this.crewNear = m;
        this.raidersNear = c;
    }

    @Override
    public String id() {
        return "ferry";
    }

    @Override
    public String title() {
        return "The Ferry Watch";
    }

    @Override
    public String rules() {
        return "Type the load crew,raiders (e.g. 1,1). Raiders may never outnumber crew on a bank. Get all to the ark.";
    }

    private List<int[]> loadsFrom(int cn, int rn, boolean near) {
        List<int[]> out = new ArrayList<>();
        int ca = near ? cn : m - cn;
        int ra = near ? rn : c - rn;
        for (int x = 0; x <= Math.min(b, ca); x++) {
            for (int y = 0; x + y <= b && y <= ra; y++) {
                if (x + y == 0) {
                    continue;
                }
                int ncn = near ? cn - x : cn + x;
                int nrn = near ? rn - y : rn + y;
                if (FerryWatch.safe(m, c, ncn, nrn)) {
                    out.add(new int[] {x, y});
                }
            }
        }
        return out;
    }

    @Override
    public List<String> legalMoves() {
        List<String> out = new ArrayList<>();
        if (!over()) {
            for (int[] l : loadsFrom(crewNear, raidersNear, ferryNear)) {
                out.add(l[0] + "," + l[1]);
            }
        }
        return Collections.unmodifiableList(out);
    }

    @Override
    public boolean play(String move) {
        if (over() || !legalMoves().contains(move == null ? "" : move.replace(" ", ""))) {
            return false;
        }
        int[] l = CabinetMoves.pair(move);
        crewNear += ferryNear ? -l[0] : l[0];
        raidersNear += ferryNear ? -l[1] : l[1];
        ferryNear = !ferryNear;
        loads.add(l);
        return true;
    }

    /** Crossings made so far. */
    public int crossings() {
        return loads.size();
    }

    /** True when the crossings so far pass the piece's own plan checker (only once everyone is across). */
    public boolean checked() {
        return FerryWatch.valid(m, c, b, loads.toArray(new int[0][]));
    }

    @Override
    public int toMove() {
        return over() ? 0 : 1;
    }

    @Override
    public boolean over() {
        return crewNear == 0 && raidersNear == 0;
    }

    @Override
    public int winner() {
        return over() ? 1 : 0;
    }

    @Override
    public String render() {
        return "near: " + "C".repeat(crewNear) + "R".repeat(raidersNear) + (ferryNear ? " [ferry]" : "")
            + "\n~~~~~~\nark:  " + "C".repeat(m - crewNear) + "R".repeat(c - raidersNear)
            + (ferryNear ? "" : " [ferry]") + "\n";
    }

    @Override
    public String hint() {
        if (over()) {
            return "";
        }
        int stride = (c + 1) * 2;
        int states = (m + 1) * stride;
        int[] firstLoad = new int[states];
        Arrays.fill(firstLoad, -1);
        int startKey = crewNear * stride + raidersNear * 2 + (ferryNear ? 0 : 1);
        boolean[] seen = new boolean[states];
        seen[startKey] = true;
        ArrayDeque<int[]> q = new ArrayDeque<>();
        List<int[]> first = loadsFrom(crewNear, raidersNear, ferryNear);
        for (int i = 0; i < first.size(); i++) {
            int[] l = first.get(i);
            int cn = crewNear - (ferryNear ? l[0] : -l[0]);
            int rn = raidersNear - (ferryNear ? l[1] : -l[1]);
            int key = cn * stride + rn * 2 + (ferryNear ? 1 : 0);
            if (!seen[key]) {
                seen[key] = true;
                firstLoad[key] = i;
                q.add(new int[] {cn, rn, ferryNear ? 1 : 0});
            }
        }
        while (!q.isEmpty()) {
            int[] s = q.poll();
            int key = s[0] * stride + s[1] * 2 + s[2];
            if (s[0] == 0 && s[1] == 0) {
                int[] l = first.get(firstLoad[key]);
                return l[0] + "," + l[1];
            }
            boolean near = s[2] == 0;
            for (int[] l : loadsFrom(s[0], s[1], near)) {
                int cn = s[0] - (near ? l[0] : -l[0]);
                int rn = s[1] - (near ? l[1] : -l[1]);
                int nk = cn * stride + rn * 2 + (near ? 1 : 0);
                if (!seen[nk]) {
                    seen[nk] = true;
                    firstLoad[nk] = firstLoad[key];
                    q.add(new int[] {cn, rn, near ? 1 : 0});
                }
            }
        }
        return legalMoves().isEmpty() ? "" : legalMoves().get(0);
    }
}
