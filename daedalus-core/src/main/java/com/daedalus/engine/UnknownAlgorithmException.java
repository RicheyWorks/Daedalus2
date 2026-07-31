// SPDX-License-Identifier: MIT

package com.daedalus.engine;

import java.util.List;
import java.util.NoSuchElementException;

/**
 * A caller named a generator or solver that is not registered.
 *
 * <h3>Why this is not just {@code NoSuchElementException}</h3>
 *
 * <p>Both registries used to throw a bare {@link NoSuchElementException}, and the REST layer had
 * no handler for it — so {@code POST /api/v1/maze/generate} with a mistyped {@code generatorId},
 * and {@code POST /api/v1/maze/&#123;id&#125;/solve/&#123;solverId&#125;} with a mistyped solver,
 * both answered <b>500 Internal Server Error</b> and logged a stack trace. A client typo is not a
 * server fault, and the two most-used endpoints in the API were the ones reporting it that way
 * while every analytical endpoint added later answers a clean 404.
 *
 * <p>The obvious patch — map {@code NoSuchElementException} to 404 globally — is worse than the
 * bug. That type is thrown by {@code Optional.get()}, {@code Iterator.next()} and any number of
 * genuine internal invariant failures; routing all of them to 404 would turn real defects into
 * quiet "not found" responses, which is exactly the sort of guard that stops guarding without
 * telling anyone. A distinct type keeps the mapping honest: only a failed registry lookup by a
 * caller-supplied id becomes a 404.
 *
 * <p>It still extends {@code NoSuchElementException} so existing {@code catch} sites and the
 * documented behaviour of {@code require(...)} are unchanged.
 *
 * <p>The exception carries the ids that <em>were</em> registered, so the 404 body can tell the
 * caller what to type instead of only what not to.
 *
 * @param kind  {@code "generator"} or {@code "solver"} — what was being looked up
 * @param id    the id the caller asked for
 * @param known every id that is registered, sorted
 */
public class UnknownAlgorithmException extends NoSuchElementException {

    private static final long serialVersionUID = 1L;

    private final String kind;
    private final String id;
    private final List<String> known;

    /**
     * @param kind  {@code "generator"} or {@code "solver"}
     * @param id    the unregistered id the caller supplied
     * @param known every registered id; copied defensively and exposed unmodifiable
     */
    public UnknownAlgorithmException(String kind, String id, List<String> known) {
        super("No " + kind + " registered with id: " + id);
        this.kind = kind;
        this.id = id;
        this.known = List.copyOf(known);
    }

    /** {@code "generator"} or {@code "solver"}. */
    public String kind() {
        return kind;
    }

    /** The id the caller asked for. */
    public String id() {
        return id;
    }

    /** Every id that is registered, sorted — what the caller could have said instead. */
    public List<String> known() {
        return known;
    }
}
