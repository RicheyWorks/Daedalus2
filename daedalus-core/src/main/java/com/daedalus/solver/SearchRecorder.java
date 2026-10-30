// SPDX-License-Identifier: MIT

package com.daedalus.solver;

import com.daedalus.graph.Graph;

import java.util.function.IntConsumer;

/**
 * The one interception point for solver replay (ADR-004's design note, built now that the web
 * UI wants to animate searches): while a recording is active on the <em>current thread</em>,
 * {@link AbstractMazeSolver#graphOf} hands solvers a decorated {@link Graph} whose
 * {@code neighbors()} reports each expansion before delegating.
 *
 * <h3>Why a thread-local, and why that is safe here</h3>
 *
 * <p>Solvers are stateless singletons and take no collaborator through their SPI, so there is
 * no constructor to inject an observer into without breaking every implementation. The
 * recording scope is confined to {@code MazeReplay.record(...)}: set, solve, clear in a
 * {@code finally} — the observer never outlives the call, concurrent solves on other threads
 * (the server solves on request threads against shared cached grids) see {@code null} and pay
 * a single thread-local read at graph construction, not per expansion.
 *
 * <p>What an "expansion" is: one {@code neighbors(node)} call — the moment a search takes a
 * node off its frontier and looks around. For BFS that is each node once, in flood order; for
 * A* it is best-first order; a re-expanding search would show its repeats honestly.
 */
public final class SearchRecorder {

    private static final ThreadLocal<IntConsumer> ACTIVE = new ThreadLocal<>();

    private SearchRecorder() {
    }

    /** Begin recording on this thread. Callers must pair with {@link #end()} in a finally. */
    public static void begin(IntConsumer onExpand) {
        ACTIVE.set(onExpand);
    }

    /** Stop recording on this thread. */
    public static void end() {
        ACTIVE.remove();
    }

    /** The graph solvers should search: decorated while recording, untouched otherwise. */
    static Graph observe(Graph graph) {
        IntConsumer observer = ACTIVE.get();
        return observer == null ? graph : new Recording(graph, observer);
    }

    private record Recording(Graph delegate, IntConsumer observer) implements Graph {
        @Override
        public int nodeCount() {
            return delegate.nodeCount();
        }

        @Override
        public int maxDegree() {
            return delegate.maxDegree();
        }

        @Override
        public int neighbors(int node, int[] out) {
            observer.accept(node);
            return delegate.neighbors(node, out);
        }

        @Override
        public double edgeWeight(int from, int to) {
            return delegate.edgeWeight(from, to);
        }
    }
}
