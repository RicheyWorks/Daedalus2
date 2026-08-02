// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Delayed;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

/**
 * A scheduler that never schedules — the test-side half of the ticker seam on
 * {@link TrafficService} and {@link LivingMazeService}.
 *
 * <p>{@code scheduleAtFixedRate} records the task and hands back a cancellable handle;
 * {@link #tick()} runs every task that has not been cancelled, once, on the calling thread.
 * That buys two things a real scheduler cannot give a test. A tick becomes a <em>statement</em>
 * rather than a wait, so a sequence like "two quiet ticks, then occupancy, then two more" is
 * exact instead of approximate and costs no wall-clock. And {@link #live()} answers the question
 * every leak in these two classes turns on: <em>how many tickers are running for this maze?</em>
 * Both services promise one however many times they are started, and both promise to leave none
 * behind when a run retires — promises whose violation a clock-watching test cannot see, because
 * a duplicated ticker does not fail, it just quietly does the work twice and outlives its owner.
 *
 * <p>Shared rather than duplicated: the two services are near-identical in shape (per-maze
 * tracker, single-threaded ticker, copy-on-write commit through the same cache), their
 * scheduling bugs are the same bugs, and a second copy of this fake would have drifted from the
 * first the moment one of them grew a method.
 */
final class ManualTicker extends ScheduledThreadPoolExecutor {

    private final List<Task> tasks = new ArrayList<>();

    ManualTicker() {
        super(0);
    }

    @Override
    public ScheduledFuture<?> scheduleAtFixedRate(Runnable command, long initialDelay,
                                                  long period, TimeUnit unit) {
        Task task = new Task(command);
        tasks.add(task);
        return task;
    }

    /** One round: every live task runs exactly once, in scheduling order. */
    void tick() {
        for (Task task : List.copyOf(tasks)) {
            if (!task.cancelled) {
                task.body.run();
            }
        }
    }

    /**
     * Runs rounds until {@code stop} answers true or the budget is spent.
     *
     * @return ticks actually run — assert on it when the count is part of the contract
     */
    int tickUntil(java.util.function.BooleanSupplier stop, int budget) {
        for (int i = 1; i <= budget; i++) {
            if (stop.getAsBoolean()) {
                return i - 1;
            }
            tick();
        }
        if (!stop.getAsBoolean()) {
            throw new AssertionError("condition never held within " + budget + " ticks");
        }
        return budget;
    }

    /** Tasks scheduled and not yet cancelled. */
    long live() {
        return tasks.stream().filter(t -> !t.cancelled).count();
    }

    private static final class Task implements ScheduledFuture<Void> {
        private final Runnable body;
        private volatile boolean cancelled;

        Task(Runnable body) {
            this.body = body;
        }

        @Override
        public boolean cancel(boolean mayInterruptIfRunning) {
            boolean first = !cancelled;
            cancelled = true;
            return first;
        }

        @Override
        public boolean isCancelled() {
            return cancelled;
        }

        @Override
        public boolean isDone() {
            return cancelled;
        }

        @Override
        public Void get() {
            return null;
        }

        @Override
        public Void get(long timeout, TimeUnit unit) {
            return null;
        }

        @Override
        public long getDelay(TimeUnit unit) {
            return 0L;
        }

        @Override
        public int compareTo(Delayed other) {
            return Long.compare(getDelay(TimeUnit.NANOSECONDS),
                    other.getDelay(TimeUnit.NANOSECONDS));
        }
    }
}
