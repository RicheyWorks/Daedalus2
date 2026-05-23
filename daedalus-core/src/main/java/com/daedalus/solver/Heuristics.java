// SPDX-License-Identifier: MIT

package com.daedalus.solver;

import com.daedalus.model.Point;

import java.util.function.ToDoubleBiFunction;

/** Heuristic catalog. Pluggable for A*, IDA*, weighted A*, etc. */
public final class Heuristics {

    private Heuristics() {}

    public static final ToDoubleBiFunction<Point, Point> MANHATTAN =
            (a, b) -> Math.abs(a.row() - b.row()) + Math.abs(a.col() - b.col());

    public static final ToDoubleBiFunction<Point, Point> EUCLIDEAN =
            Point::euclidean;

    public static final ToDoubleBiFunction<Point, Point> CHEBYSHEV =
            (a, b) -> Math.max(Math.abs(a.row() - b.row()), Math.abs(a.col() - b.col()));

    /** Tie-breaker: small bias toward straight-line preference. */
    public static ToDoubleBiFunction<Point, Point> manhattanWithTieBreaker(double epsilon) {
        return (a, b) -> {
            double m = Math.abs(a.row() - b.row()) + Math.abs(a.col() - b.col());
            return m * (1.0 + epsilon);
        };
    }
}
