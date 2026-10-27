// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayList;
import java.util.List;

/**
 * G452 The Harbour Wards: each lighthouse (an integer site) guards the part of the harbour box
 * nearer to it than to any other lighthouse, its Voronoi cell. Each cell is the box clipped by the
 * perpendicular-bisector half-plane toward every other site (Sutherland-Hodgman), O(n^2) clips
 * overall. Takes 1 to 300 distinct sites within 10^6 and a box {x0, y0, x1, y1} with x0 &lt; x1 and
 * y0 &lt; y1 within 10^6. Cells are counter-clockwise {x, y} corner lists; a cell can be empty
 * when its site lies outside the box and is beaten everywhere inside it.
 */
public final class HarbourWards {

    public static final String QUEST_ID = "q_harbour_wards";
    public static final int MAX_SITES = 300;
    public static final long MAX_COORD = 1_000_000;

    private HarbourWards() { }

    private static void check(long[][] sites, long[] box) {
        if (sites == null || sites.length < 1 || sites.length > MAX_SITES) {
            throw new IllegalArgumentException("need 1 to " + MAX_SITES + " sites");
        }
        if (box == null || box.length != 4 || box[0] >= box[2] || box[1] >= box[3]) {
            throw new IllegalArgumentException("box is {x0, y0, x1, y1} with x0 < x1 and y0 < y1");
        }
        for (long v : box) {
            if (Math.abs(v) > MAX_COORD) {
                throw new IllegalArgumentException("box within 10^6");
            }
        }
        for (int i = 0; i < sites.length; i++) {
            long[] s = sites[i];
            if (s == null || s.length != 2 || Math.abs(s[0]) > MAX_COORD || Math.abs(s[1]) > MAX_COORD) {
                throw new IllegalArgumentException("sites are {x, y} within 10^6");
            }
            for (int j = 0; j < i; j++) {
                if (sites[j][0] == s[0] && sites[j][1] == s[1]) {
                    throw new IllegalArgumentException("repeated site");
                }
            }
        }
    }

    /** Keep the part of poly with a*x + b*y &lt;= c. */
    private static List<double[]> clip(List<double[]> poly, double a, double b, double c) {
        List<double[]> out = new ArrayList<>();
        int n = poly.size();
        for (int i = 0; i < n; i++) {
            double[] p = poly.get(i);
            double[] q = poly.get((i + 1) % n);
            double fp = a * p[0] + b * p[1] - c;
            double fq = a * q[0] + b * q[1] - c;
            if (fp <= 0) {
                out.add(p);
            }
            if (fp < 0 && fq > 0 || fp > 0 && fq < 0) {
                double t = fp / (fp - fq);
                out.add(new double[] {p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])});
            }
        }
        return out;
    }

    /** The ward of site i: counter-clockwise corners, possibly none. */
    public static double[][] cell(long[][] sites, long[] box, int i) {
        check(sites, box);
        if (i < 0 || i >= sites.length) {
            throw new IllegalArgumentException("no such site");
        }
        List<double[]> poly = new ArrayList<>();
        poly.add(new double[] {box[0], box[1]});
        poly.add(new double[] {box[2], box[1]});
        poly.add(new double[] {box[2], box[3]});
        poly.add(new double[] {box[0], box[3]});
        long[] s = sites[i];
        for (int j = 0; j < sites.length && !poly.isEmpty(); j++) {
            if (j == i) {
                continue;
            }
            long[] o = sites[j];
            double a = 2.0 * (o[0] - s[0]);
            double b = 2.0 * (o[1] - s[1]);
            double c = (double) (o[0] * o[0] + o[1] * o[1]) - (double) (s[0] * s[0] + s[1] * s[1]);
            poly = clip(poly, a, b, c);
        }
        return poly.toArray(new double[0][]);
    }

    /** Area of a counter-clockwise corner list (shoelace). */
    public static double area(double[][] poly) {
        double s = 0;
        for (int i = 0; i < poly.length; i++) {
            double[] p = poly[i];
            double[] q = poly[(i + 1) % poly.length];
            s += p[0] * q[1] - p[1] * q[0];
        }
        return s / 2;
    }

    /** Quest q_harbour_wards: the harbour master names site i's ward area, rounded to nearest. */
    public static boolean quest(long[][] sites, long[] box, int i, long answer) {
        return Math.round(area(cell(sites, box, i))) == answer;
    }
}