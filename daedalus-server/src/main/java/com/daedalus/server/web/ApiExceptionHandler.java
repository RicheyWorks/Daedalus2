// SPDX-License-Identifier: MIT

package com.daedalus.server.web;

import com.daedalus.engine.UnknownAlgorithmException;
import com.daedalus.server.ratelimit.RateLimitNaming;
import io.github.resilience4j.ratelimiter.RateLimiter;
import io.github.resilience4j.ratelimiter.RateLimiterRegistry;
import io.github.resilience4j.ratelimiter.RequestNotPermitted;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.ConstraintViolationException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.FieldError;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import java.net.URI;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * Centralised exception → HTTP translation for the REST surface.
 *
 * <p>Two responsibilities, both ride the same {@link ProblemDetail} (RFC 7807) format so
 * any consumer gets a predictable shape:
 * <ol>
 *   <li><b>Validation failures</b> ({@code @Valid} on bodies, {@code @Validated} on path /
 *       query params) become {@code 400} with a {@code fieldErrors} map keyed by the offending
 *       field. Malformed JSON and bad type coercion (non-UUID where a UUID is expected, etc.)
 *       collapse into the same 400 path.</li>
 *   <li><b>Rate limiting</b> — Resilience4j throws {@link RequestNotPermitted} when an instance
 *       is empty. We surface that as {@code 429 Too Many Requests} plus a {@code Retry-After}
 *       header (in seconds, conservatively rounded up) so well-behaved clients can back off.</li>
 * </ol>
 *
 * <p>Ordered {@link Ordered#HIGHEST_PRECEDENCE} so this advice wins over Spring Boot's
 * default {@code DefaultErrorAttributes}-driven path.
 *
 * <h3>The contract is "every error", and it used not to be</h3>
 *
 * <p>An audit on 2026-07-31 drove twenty-one distinct failure modes at a running server and
 * compared the bodies. Five were outside the RFC 7807 contract this class exists to provide:
 * a missing required parameter, the wrong HTTP verb, an unsupported {@code Content-Type} and an
 * unmapped path all fell through to Boot's {@code {timestamp, status, error, path}} default, and
 * an unregistered generator or solver id answered <b>500 with a stack trace</b> for what is
 * plainly a client typo. The status codes mostly looked right from the outside, which is why
 * nothing had noticed — a client reading {@code detail} and {@code title} off those responses got
 * nulls from a reply that otherwise seemed fine.
 *
 * <p>The lesson is in the shape of the gap rather than any one handler: an error contract is only
 * as good as the least-travelled path that produces an error, and the least-travelled paths are
 * exactly the ones no test drives. {@code ErrorContractTest} now drives them, generated from the
 * controller sources rather than from a list somebody maintains.
 */
@RestControllerAdvice
@Order(Ordered.HIGHEST_PRECEDENCE)
public class ApiExceptionHandler {

    private static final URI VALIDATION_TYPE  = URI.create("https://daedalus.dev/problems/validation");
    private static final URI MALFORMED_TYPE   = URI.create("https://daedalus.dev/problems/malformed-request");
    private static final URI RATE_LIMIT_TYPE  = URI.create("https://daedalus.dev/problems/rate-limited");
    private static final URI UNKNOWN_ALGORITHM_TYPE =
            URI.create("https://daedalus.dev/problems/unknown-algorithm");
    private static final URI NOT_FOUND_TYPE   = URI.create("https://daedalus.dev/problems/not-found");

    /**
     * Optional registry of named Resilience4j rate limiters. When present (the normal Spring
     * runtime, where Resilience4j Spring Boot auto-config supplies it), {@link #onRateLimited}
     * looks up the offending limiter and reports its actual {@code limit-refresh-period} as
     * {@code Retry-After}. When null (unit tests, or any context without Resilience4j
     * autowired), the handler falls back to a 1-second floor.
     */
    private final RateLimiterRegistry rateLimiterRegistry;

    /**
     * No-arg constructor — used by tests that construct the advice manually for
     * {@code MockMvcBuilders.standaloneSetup(...)}, where {@code Retry-After} accuracy
     * isn't the contract under test. Production wiring goes through the
     * {@code @Autowired} constructor below.
     */
    public ApiExceptionHandler() {
        this.rateLimiterRegistry = null;
    }

    /**
     * Spring-managed constructor. Resilience4j Spring Boot auto-config exposes a
     * {@link RateLimiterRegistry} bean populated from {@code resilience4j.ratelimiter.instances.*}
     * in the active profile's YAML; we use it to compute an honest {@code Retry-After}
     * value rather than the 1-second placeholder we used to ship.
     */
    @Autowired
    public ApiExceptionHandler(RateLimiterRegistry rateLimiterRegistry) {
        this.rateLimiterRegistry = rateLimiterRegistry;
    }

    /**
     * {@code @Valid} on a {@code @RequestBody} failed. Pulls every {@link FieldError} off
     * the binding result and surfaces them as a {@code fieldErrors} map; an extra
     * {@code globalErrors} list catches class-level constraint violations.
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ProblemDetail onBodyValidation(MethodArgumentNotValidException ex) {
        Map<String, String> fieldErrors = new TreeMap<>();
        for (FieldError fe : ex.getBindingResult().getFieldErrors()) {
            // First message wins if a field has multiple violations — keeps the body terse.
            fieldErrors.putIfAbsent(fe.getField(),
                    fe.getDefaultMessage() == null ? "invalid" : fe.getDefaultMessage());
        }
        List<String> globalErrors = ex.getBindingResult().getGlobalErrors().stream()
                .map(e -> e.getDefaultMessage() == null ? "invalid" : e.getDefaultMessage())
                .toList();

        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.BAD_REQUEST, "Request body failed validation");
        pd.setTitle("Validation failed");
        pd.setType(VALIDATION_TYPE);
        pd.setProperty("fieldErrors", fieldErrors);
        if (!globalErrors.isEmpty()) {
            pd.setProperty("globalErrors", globalErrors);
        }
        return pd;
    }

    /**
     * {@code @Validated} on the controller class plus {@code @Min}/{@code @Max}/{@code @Pattern}
     * on path or query params. Constraint violations come back keyed by
     * {@code methodName.argumentName}; we trim that to just the argument name so the body
     * mirrors the {@link #onBodyValidation} format.
     */
    @ExceptionHandler(ConstraintViolationException.class)
    public ProblemDetail onParamValidation(ConstraintViolationException ex) {
        Map<String, String> fieldErrors = new LinkedHashMap<>();
        for (ConstraintViolation<?> v : ex.getConstraintViolations()) {
            String path = v.getPropertyPath().toString();
            int dot = path.lastIndexOf('.');
            String field = dot < 0 ? path : path.substring(dot + 1);
            fieldErrors.putIfAbsent(field, v.getMessage());
        }
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.BAD_REQUEST, "Request parameter failed validation");
        pd.setTitle("Validation failed");
        pd.setType(VALIDATION_TYPE);
        pd.setProperty("fieldErrors", fieldErrors);
        return pd;
    }

    /** Body wasn't valid JSON (or couldn't be deserialized into the target type at all). */
    /**
     * Caller errors that surface as {@link IllegalArgumentException} from the service layer —
     * e.g. a hotspot outside the requested maze's bounds. These are 400s, not 500s: the
     * request was well-formed but semantically wrong, and the message is written for the
     * caller (services must keep them free of internals).
     */
    @ExceptionHandler(IllegalArgumentException.class)
    public ProblemDetail onIllegalArgument(IllegalArgumentException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.BAD_REQUEST, ex.getMessage() == null ? "invalid request" : ex.getMessage());
        pd.setTitle("Invalid request");
        pd.setType(VALIDATION_TYPE);
        return pd;
    }

    /**
     * First Identify used to train on the request thread (~40s). The fit now runs on a
     * dedicated trainer; until it publishes, the answer is 503 with Retry-After, not a
     * stuck Tomcat worker.
     */
    @ExceptionHandler(com.daedalus.server.service.FingerprintService.ClassifierWarmingException.class)
    public ResponseEntity<ProblemDetail> onClassifierWarming(
            com.daedalus.server.service.FingerprintService.ClassifierWarmingException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.SERVICE_UNAVAILABLE, ex.getMessage());
        pd.setTitle("Classifier warming");
        pd.setType(URI.create("https://daedalus.dev/problems/classifier-warming"));
        pd.setProperty("kind", "classifier-warming");
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .header(HttpHeaders.RETRY_AFTER, "5")
                .contentType(MediaType.APPLICATION_PROBLEM_JSON).body(pd);
    }

    /**
     * The living-maze ticker is full ({@code daedalus.living.max-concurrent} runs already
     * animating). 409 rather than 429: the caller's quota is fine — the shared resource is
     * busy, and retrying after a run settles will succeed.
     */
    @ExceptionHandler(com.daedalus.server.service.LivingMazeService.CapacityExceededException.class)
    public ResponseEntity<ProblemDetail> onLivingCapacity(
            com.daedalus.server.service.LivingMazeService.CapacityExceededException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, ex.getMessage());
        pd.setTitle("Too many living mazes");
        pd.setType(URI.create("https://daedalus.dev/problems/living-capacity"));
        pd.setProperty("kind", "living-capacity");
        return ResponseEntity.status(HttpStatus.CONFLICT)
                .contentType(MediaType.APPLICATION_PROBLEM_JSON).body(pd);
    }

    /**
     * A solver spent its node budget without finding a route.
     *
     * <p>422 rather than 500 or 504: the request is well formed and the server is healthy — this
     * particular algorithm cannot answer for this particular maze inside a sane cost. It is also
     * not 404 or an empty path, because the maze is very likely solvable and every other solver
     * will say so. Measured, this fires for IDA* on dungeons from about 21x21 up, where the
     * unguarded search took 16 seconds at 21x21 and over 300 without finishing at 25x25.
     */
    @ExceptionHandler(com.daedalus.solver.SolverBudgetExceededException.class)
    public ResponseEntity<ProblemDetail> onSolverBudget(
            com.daedalus.solver.SolverBudgetExceededException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.UNPROCESSABLE_CONTENT, ex.getMessage());
        pd.setTitle("Solver gave up");
        pd.setType(URI.create("https://daedalus.dev/problems/solver-budget"));
        pd.setProperty("kind", "solver-budget");
        pd.setProperty("solver", ex.solverId());
        pd.setProperty("nodeBudget", ex.budget());
        return ResponseEntity.status(HttpStatus.UNPROCESSABLE_CONTENT)
                .contentType(MediaType.APPLICATION_PROBLEM_JSON).body(pd);
    }

    /**
     * Join refused: the session finished, or it already has {@code MAX_PLAYERS}.
     * Both are 409; the type tells the client whether to wait or pick another room.
     */
    @ExceptionHandler(com.daedalus.server.service.GameSessionService.JoinRefusedException.class)
    public ResponseEntity<ProblemDetail> onJoinRefused(
            com.daedalus.server.service.GameSessionService.JoinRefusedException ex) {
        boolean done = ex.reason()
                == com.daedalus.server.service.GameSessionService.JoinRefusedException.Reason.COMPLETED;
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, ex.getMessage());
        pd.setTitle(done ? "Session completed" : "Session full");
        pd.setType(URI.create(done
                ? "https://daedalus.dev/problems/session-completed"
                : "https://daedalus.dev/problems/session-full"));
        pd.setProperty("kind", done ? "session-completed" : "session-full");
        return ResponseEntity.status(HttpStatus.CONFLICT)
                .contentType(MediaType.APPLICATION_PROBLEM_JSON).body(pd);
    }

    /** Traffic's tracker pool is full — same 409 posture as the living-maze ticker. */
    @ExceptionHandler(com.daedalus.server.service.TrafficService.CapacityExceededException.class)
    public ResponseEntity<ProblemDetail> onTrafficCapacity(
            com.daedalus.server.service.TrafficService.CapacityExceededException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, ex.getMessage());
        pd.setTitle("Too many tracked mazes");
        pd.setType(URI.create("https://daedalus.dev/problems/traffic-capacity"));
        pd.setProperty("kind", "traffic-capacity");
        return ResponseEntity.status(HttpStatus.CONFLICT)
                .contentType(MediaType.APPLICATION_PROBLEM_JSON).body(pd);
    }

    /** Session store is full — refuse the new open; do not LRU-evict a mid-hunt session. */
    @ExceptionHandler(com.daedalus.server.service.GameSessionService.CapacityExceededException.class)
    public ResponseEntity<ProblemDetail> onSessionCapacity(
            com.daedalus.server.service.GameSessionService.CapacityExceededException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, ex.getMessage());
        pd.setTitle("Too many live sessions");
        pd.setType(URI.create("https://daedalus.dev/problems/session-capacity"));
        pd.setProperty("kind", "session-capacity");
        return ResponseEntity.status(HttpStatus.CONFLICT)
                .contentType(MediaType.APPLICATION_PROBLEM_JSON).body(pd);
    }

    /** Agent walk store is full — same 409 posture as the session pool. */
    @ExceptionHandler(com.daedalus.server.service.AgentWalkService.CapacityExceededException.class)
    public ResponseEntity<ProblemDetail> onAgentCapacity(
            com.daedalus.server.service.AgentWalkService.CapacityExceededException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, ex.getMessage());
        pd.setTitle("Too many agent walks");
        pd.setType(URI.create("https://daedalus.dev/problems/agent-capacity"));
        pd.setProperty("kind", "agent-capacity");
        return ResponseEntity.status(HttpStatus.CONFLICT)
                .contentType(MediaType.APPLICATION_PROBLEM_JSON).body(pd);
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ProblemDetail onMalformedBody(HttpMessageNotReadableException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.BAD_REQUEST, "Request body could not be parsed");
        pd.setTitle("Malformed request");
        pd.setType(MALFORMED_TYPE);
        return pd;
    }

    /**
     * A caller named a generator or solver that is not registered — {@code 404}, not {@code 500}.
     *
     * <p>This was the API's worst error: {@code POST /api/v1/maze/generate} with a mistyped
     * {@code generatorId} and {@code POST /api/v1/maze/&#123;id&#125;/solve/&#123;solverId&#125;}
     * with a mistyped solver both answered <b>500</b> and logged a stack trace, because the
     * registries threw a bare {@code NoSuchElementException} that nothing here handled. The two
     * most-used endpoints in the API were the two reporting a typo as a server fault, while every
     * analytical endpoint added later answered a clean 404. Mapping {@code NoSuchElementException}
     * itself would have been the wrong repair — see {@link UnknownAlgorithmException}.
     *
     * <p>The body lists the ids that <em>are</em> registered, so the answer tells the caller what
     * to type rather than only that they were wrong.
     */
    @ExceptionHandler(UnknownAlgorithmException.class)
    public ResponseEntity<ProblemDetail> onUnknownAlgorithm(UnknownAlgorithmException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND,
                "No " + ex.kind() + " is registered with id '" + ex.id() + "'");
        pd.setTitle("Unknown " + ex.kind());
        pd.setType(UNKNOWN_ALGORITHM_TYPE);
        pd.setProperty("kind", ex.kind());
        pd.setProperty("requested", ex.id());
        pd.setProperty("known", ex.known());
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .contentType(MediaType.APPLICATION_PROBLEM_JSON).body(pd);
    }

    /**
     * The addressed resource is not here — the 404 that used to have no body at all.
     *
     * <p>27 call sites answered {@code ResponseEntity.notFound().build()}, which is a 404 with
     * nothing in it. See {@link ResourceNotFoundException} for why that mattered and what the
     * distinctions between those sites turned out to be.
     */
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ProblemDetail> onResourceNotFound(ResourceNotFoundException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        pd.setTitle("No such " + ex.kind());
        pd.setType(NOT_FOUND_TYPE);
        pd.setProperty("kind", ex.kind());
        pd.setProperty("requested", ex.requested());
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .contentType(MediaType.APPLICATION_PROBLEM_JSON).body(pd);
    }

    /**
     * A required query parameter was absent.
     *
     * <p>Spring resolves this one itself by default, which is why it looked handled: the caller
     * got a 400, just not <em>this</em> API's 400. The body was Boot's
     * {@code {timestamp, status, error, path}} shape, so a client written against the documented
     * RFC 7807 contract — reading {@code detail} and {@code title} — got nulls from a response
     * that otherwise looked fine. Silent shape drift is worse than a wrong status code.
     */
    @ExceptionHandler(MissingServletRequestParameterException.class)
    public ProblemDetail onMissingParam(MissingServletRequestParameterException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST,
                "Required parameter '" + ex.getParameterName() + "' is missing");
        pd.setTitle("Missing parameter");
        pd.setType(MALFORMED_TYPE);
        pd.setProperty("fieldErrors",
                Map.of(ex.getParameterName(), "is required"));
        return pd;
    }

    /**
     * Right path, wrong verb. Carries the {@code Allow} header RFC 9110 §15.5.6 requires, which
     * Boot's default path does set — but its body was the default shape, so this was the same
     * silent contract break as {@link #onMissingParam}.
     */
    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<ProblemDetail> onMethodNotAllowed(
            HttpRequestMethodNotSupportedException ex) {
        var allowed = ex.getSupportedHttpMethods();
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.METHOD_NOT_ALLOWED,
                "Method " + ex.getMethod() + " is not supported on this path");
        pd.setTitle("Method not allowed");
        pd.setType(MALFORMED_TYPE);
        pd.setProperty("allowed", allowed == null ? List.of()
                : allowed.stream().map(Object::toString).sorted().toList());
        HttpHeaders headers = new HttpHeaders();
        if (allowed != null && !allowed.isEmpty()) {
            headers.setAllow(allowed);
        }
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED).headers(headers)
                .contentType(MediaType.APPLICATION_PROBLEM_JSON).body(pd);
    }

    /** A body arrived as something this API does not parse — {@code 415}, in the house shape. */
    @ExceptionHandler(HttpMediaTypeNotSupportedException.class)
    public ProblemDetail onUnsupportedMediaType(HttpMediaTypeNotSupportedException ex) {
        var offered = ex.getContentType();
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.UNSUPPORTED_MEDIA_TYPE,
                "Content-Type " + (offered == null ? "(absent)" : offered) + " is not supported");
        pd.setTitle("Unsupported media type");
        pd.setType(MALFORMED_TYPE);
        pd.setProperty("supported",
                ex.getSupportedMediaTypes().stream().map(Object::toString).sorted().toList());
        return pd;
    }

    /**
     * No handler matched the path at all — a typo'd URL, or a client built against a route that
     * no longer exists. Answering in the house shape means "this endpoint does not exist" and
     * "this maze does not exist" are told apart by {@code title}, not by guessing from a 404
     * with an empty body.
     */
    @ExceptionHandler(NoResourceFoundException.class)
    public ProblemDetail onNoHandler(NoResourceFoundException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND,
                "No endpoint at " + ex.getHttpMethod() + " /" + ex.getResourcePath());
        pd.setTitle("No such endpoint");
        pd.setType(NOT_FOUND_TYPE);
        return pd;
    }

    /** A path or query param couldn't be coerced (non-UUID UUID, non-int int, etc.). */
    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ProblemDetail onTypeMismatch(MethodArgumentTypeMismatchException ex) {
        Class<?> required = ex.getRequiredType();
        String requiredName = required == null ? "(unknown)" : required.getSimpleName();
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.BAD_REQUEST,
                "Parameter '" + ex.getName() + "' must be a " + requiredName);
        pd.setTitle("Invalid parameter");
        pd.setType(MALFORMED_TYPE);
        pd.setProperty("fieldErrors", Map.of(ex.getName(), "must be a " + requiredName));
        return pd;
    }

    /**
     * Resilience4j refused the call (limiter empty, no waiting capacity). The exception
     * carries a name string; we translate to a 429 with a {@code Retry-After} header whose
     * value is the limiter's configured {@code limit-refresh-period} in seconds (rounded up,
     * floored at 1 per RFC 9110 §10.2.3 — the header takes a whole number of seconds).
     *
     * <p>This is a worst-case bound rather than the precise wait — Resilience4j's standard
     * limiters refresh permits in a single burst at the end of each refresh period, so the
     * actual wait is somewhere in {@code (0, refreshPeriod]}. Reporting the upper bound is
     * the safest contract for clients implementing back-off: tells them not to hammer.
     *
     * <p>The instance name is exposed in the body via {@code limiter}, which lets clients
     * differentiate (e.g. "your generate quota is gone but solve is still open") without
     * encoding business meaning into the HTTP layer.
     */
    @ExceptionHandler(RequestNotPermitted.class)
    public ResponseEntity<ProblemDetail> onRateLimited(RequestNotPermitted ex) {
        // The exception's getMessage() embeds the limiter name as "RateLimiter '<name>' does not permit further calls".
        // Per-key limiters are named "<base>::<callerKey>" (see RateLimitNaming); collapse back to the base so the
        // body reports a stable "mazeGenerate" and never leaks the caller's IP or subject. Plain (global) names,
        // which carry no separator, pass through unchanged.
        String limiterName = RateLimitNaming.baseOf(extractLimiterName(ex.getMessage()));
        long retryAfterSeconds = computeRetryAfterSeconds(limiterName);

        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.TOO_MANY_REQUESTS,
                "Rate limit exceeded — try again shortly");
        pd.setTitle("Too many requests");
        pd.setType(RATE_LIMIT_TYPE);
        pd.setProperty("limiter", limiterName);
        pd.setProperty("retryAfterSeconds", retryAfterSeconds);

        HttpHeaders headers = new HttpHeaders();
        headers.set(HttpHeaders.RETRY_AFTER, Long.toString(retryAfterSeconds));
        headers.setContentType(MediaType.APPLICATION_PROBLEM_JSON);
        return new ResponseEntity<>(pd, headers, HttpStatus.TOO_MANY_REQUESTS);
    }

    /**
     * Compute the {@code Retry-After} value in whole seconds for the named limiter. Looks
     * up the limiter in {@link #rateLimiterRegistry} and reads its
     * {@code limit-refresh-period}. Several defensive fallbacks land on {@code 1L}:
     * <ul>
     *   <li>no registry was injected (test setup, or Resilience4j absent);</li>
     *   <li>the limiter name couldn't be parsed off the exception message;</li>
     *   <li>the registry has no instance under that name;</li>
     *   <li>any unexpected runtime hiccup looking up the config (registry should be
     *       a stable, app-startup-populated structure but defensive nulls keep one
     *       misconfigured limiter from making 429 itself fail).</li>
     * </ul>
     * The 1-second floor matches the previous hardcoded behaviour and respects the
     * RFC 9110 requirement that {@code Retry-After} carry a whole-number-of-seconds
     * value of at least 1.
     */
    private long computeRetryAfterSeconds(String limiterName) {
        if (rateLimiterRegistry == null || "unknown".equals(limiterName)) {
            return 1L;
        }
        try {
            RateLimiter rl = rateLimiterRegistry.find(limiterName).orElse(null);
            if (rl == null) {
                return 1L;
            }
            Duration refresh = rl.getRateLimiterConfig().getLimitRefreshPeriod();
            // Round UP — toMillis()/1000 truncates, which would under-report sub-second
            // surplus and tell the client to retry slightly too early.
            long ceilSeconds = (refresh.toMillis() + 999L) / 1000L;
            return Math.max(1L, ceilSeconds);
        } catch (RuntimeException defensive) {
            return 1L;
        }
    }

    /**
     * Pull the limiter name out of the standard Resilience4j message format.
     * Falls back to {@code "unknown"} if the format ever changes upstream.
     */
    private static String extractLimiterName(String message) {
        if (message == null) return "unknown";
        int first = message.indexOf('\'');
        int second = message.indexOf('\'', first + 1);
        if (first < 0 || second < 0) return "unknown";
        return message.substring(first + 1, second);
    }
}
