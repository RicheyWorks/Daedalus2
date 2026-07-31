// SPDX-License-Identifier: MIT

package com.daedalus.server.web;

/**
 * The resource a caller addressed is not here — thrown so the 404 can carry a body.
 *
 * <h3>What this replaced</h3>
 *
 * <p>{@code return ResponseEntity.notFound().build();} appeared 27 times across three
 * controllers, each answering 404 with nothing in it. After the error-contract audit made every
 * other failure mode an RFC 7807 problem detail, those 27 were the last hole — and they produced
 * a perverse inversion: a typo'd URL came back with a helpful problem detail while an expired
 * maze id came back with silence. The expired maze is the common case by a wide margin, because
 * mazes live in a bounded Caffeine cache and get evicted, and it is the one the caller can
 * actually act on ("generate a new one").
 *
 * <h3>Why an exception rather than a helper method</h3>
 *
 * <p>The direct repair — a helper returning a populated {@code ResponseEntity} — does not
 * type-check: {@code ResponseEntity<AnalysisResponse>} cannot carry a {@code ProblemDetail} body,
 * so every affected method would have had to widen its return type to {@code Object} and lose
 * its signature as documentation. Throwing sidesteps that completely and puts the formatting in
 * one place.
 *
 * <h3>The distinctions this makes visible</h3>
 *
 * <p>All 27 sites used to answer identically. Several were never the same thing:
 * <ul>
 *   <li>{@code POST /session/&#123;id&#125;/move} 404s both when the session is unknown
 *       <em>and</em> when the session is fine but its maze has been evicted from the cache — very
 *       different problems for the caller, previously indistinguishable;</li>
 *   <li>{@code GET /maze/&#123;id&#125;/ghost} 404s when the maze is unknown and when the maze is
 *       fine but nobody has completed a run on it yet — the second is not an error at all, it is
 *       "come back later";</li>
 *   <li>{@code GET /complexity} 404s for an unregistered generator and for a metric that is not
 *       measured. The first is now an {@link com.daedalus.engine.UnknownAlgorithmException} that
 *       lists all 23 generators; the second names the metrics that exist.</li>
 * </ul>
 *
 * <h3>One deliberate non-distinction</h3>
 *
 * <p>{@code POST /session/&#123;id&#125;/join} answers 404 when multiplayer is switched off,
 * specifically so the endpoint looks absent rather than disabled. That disguise has to survive
 * this change, so it throws the <em>same</em> "no such session" body an unknown id produces. A
 * more helpful message there would be a feature-flag oracle.
 *
 * @see ApiExceptionHandler#onResourceNotFound
 */
public class ResourceNotFoundException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    private final String kind;
    private final String requested;

    /**
     * @param kind      what was being looked up — {@code "maze"}, {@code "session"},
     *                  {@code "agent"}, {@code "metric"}, {@code "ghost run"}
     * @param requested the id or name the caller supplied, for echoing back
     * @param detail    a sentence written for the caller, ideally saying what to do next
     */
    public ResourceNotFoundException(String kind, String requested, String detail) {
        super(detail);
        this.kind = kind;
        this.requested = requested;
    }

    /** A maze id that is not in the cache — the most common 404 this API produces. */
    public static ResourceNotFoundException maze(Object id) {
        return new ResourceNotFoundException("maze", String.valueOf(id),
                "No maze " + id + " is available. Mazes are held in a bounded cache and are "
                        + "evicted as newer ones arrive, so a maze that existed earlier may be "
                        + "gone; generate it again with the same seed to get an identical one.");
    }

    /** A session id that is not open. Also the answer when multiplayer is off — see class doc. */
    public static ResourceNotFoundException session(Object id) {
        return new ResourceNotFoundException("session", String.valueOf(id),
                "No session " + id + " is open.");
    }

    /** An agent walk that is not open. */
    public static ResourceNotFoundException agent(Object id) {
        return new ResourceNotFoundException("agent", String.valueOf(id),
                "No agent walk " + id + " is open.");
    }

    /** What kind of thing was missing. */
    public String kind() {
        return kind;
    }

    /** The id or name the caller supplied. */
    public String requested() {
        return requested;
    }
}
