// SPDX-License-Identifier: MIT

package com.yourcompany.loadbalancer;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.HilbertCurveGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Deque;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.PriorityQueue;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Sketch: load-aware routing on top of a Daedalus Hilbert-curve topology.
 *
 * <p>Generates a {@link HilbertCurveGenerator} grid once at construction, treats every passage
 * cell as a routable node, and exposes {@link #findBestRoute(Point, Point)} which picks the
 * minimum-cost path under live load values fed in via {@link #updateNodeLoad(int, int, double)}.
 *
 * <h3>Why Dijkstra and not the bundled {@code AStarSolver}?</h3>
 *
 * The bundled {@code AStarSolver} assumes uniform edge cost (every step costs 1) and
 * {@code AStarSolver(ToDoubleBiFunction&lt;Point,Point&gt;)} only customises the <i>heuristic</i>
 * h(n), i.e. the estimated remaining cost from {@code n} to the goal. Putting per-node load
 * into h(n) — as an earlier draft of this file did — looks like it should "penalise loaded
 * nodes", but it actually breaks A* in two ways: it makes h(n) inadmissible (so the path A*
 * returns is no longer guaranteed optimal), and it doesn't change which nodes the algorithm
 * actually prefers, because the {@code g}-score still uses uniform edge costs.
 *
 * <p>Load is a property of <i>arriving at a node</i>, so it belongs in the edge cost, not the
 * heuristic. We therefore run Dijkstra directly over {@link MazeGrid#openNeighbors(Point)} with
 * edge cost {@code 1.0 + LOAD_PENALTY * load(destination)}. Same data structure, correct
 * semantics. If you later need a heuristic boost on top of Dijkstra, the same loop with an
 * added admissible h(n) (Manhattan distance to goal) gives you weighted A*.
 *
 * <h3>Caveats</h3>
 *
 * <ul>
 *   <li>Hilbert-curve mazes are space-filling curves — visually striking, locality-preserving,
 *       but not topologically representative of real network meshes (which have hubs and
 *       clusters). This sketch is appropriate for demos and load testing, not for modelling
 *       a production network shape.</li>
 *   <li>Reads of {@code currentLoad} 