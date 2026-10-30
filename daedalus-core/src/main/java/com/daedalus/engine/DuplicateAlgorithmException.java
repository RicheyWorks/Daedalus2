// SPDX-License-Identifier: MIT

package com.daedalus.engine;

/**
 * Something tried to register an algorithm id that is already taken.
 *
 * <h3>What this closes</h3>
 *
 * <p>Both registries stored their contents in a map and registered with a bare {@code put}, so a
 * second registration under an existing id silently replaced the first. That is not an abstract
 * concern: {@code PluginContext} hands every plugin the <em>live</em> {@code GeneratorRegistry}
 * and {@code SolverRegistry}, so any third-party JAR dropped in the plugins directory could
 * declare {@code id() == "recursive-backtracker"} and become it.
 *
 * <p>Measured on 2026-07-31 with a hostile generator: the registry's size did not change (2 → 2),
 * {@code /api/v1/algorithms} still advertised the id — now carrying the impostor's description —
 * and {@code require("recursive-backtracker")} returned the impostor. Every claim the project
 * makes about reproducibility runs through that lookup: the daily challenge, campaign stages, the
 * seeded tour, and the cross-process digests in {@code DeterminismGoldenTest}. A plugin could
 * change all of them and the only visible symptom would be that yesterday's seed produces a
 * different maze.
 *
 * <p>There was also no way back. Neither registry has an unregister, so the substitution outlives
 * the plugin that made it for the rest of the process's life.
 *
 * <h3>Why refuse rather than warn</h3>
 *
 * <p>A warning is a log line nobody reads on a server that boots unattended, and the state it
 * describes is unrecoverable. Refusing costs nothing: {@code PluginManager} already contains a
 * throwing plugin, marks it {@code FAILED}, and boots the rest, and the plugin subsystem's health
 * indicator already reports the failure with its description. So a colliding plugin now fails to
 * load, by the same route as any other broken plugin, and the built-in it wanted to replace keeps
 * working. First registration wins, and built-ins are registered first — from the constructor,
 * before any plugin exists.
 *
 * @param kind  {@code "generator"} or {@code "solver"}
 * @param id    the contested id
 */
public class DuplicateAlgorithmException extends IllegalStateException {

    private static final long serialVersionUID = 1L;

    private final String kind;
    private final String id;

    /**
     * @param kind      {@code "generator"} or {@code "solver"}
     * @param id        the id both algorithms claim
     * @param incumbent the class already registered under it
     * @param rejected  the class refused
     */
    public DuplicateAlgorithmException(String kind, String id, Class<?> incumbent,
                                       Class<?> rejected) {
        super("A " + kind + " with id '" + id + "' is already registered ("
                + incumbent.getName() + "); " + rejected.getName() + " was refused. "
                + "Algorithm ids are unique and first registration wins — built-ins register "
                + "before any plugin. Give the new " + kind + " a distinct id.");
        this.kind = kind;
        this.id = id;
    }

    /** {@code "generator"} or {@code "solver"}. */
    public String kind() {
        return kind;
    }

    /** The contested id. */
    public String id() {
        return id;
    }
}
