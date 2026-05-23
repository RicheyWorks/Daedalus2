// SPDX-License-Identifier: MIT

package com.daedalus.server.web;

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
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

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
 */
@RestControllerAdvice
@Order(Ordered.HIGHEST_PRECEDENCE)
public class ApiExceptionHandler {

    private static final URI VALIDATION_TYPE  = URI.create("https://daedalus.dev/problems/validation");
    private static final URI MALFORMED_TYPE   = URI.create("https://daedalus.dev/problems/malformed-request");
    private static final URI RATE_LIMIT_TYPE  = URI.create("https://daedalus.dev/problems/rate-limited");

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
    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ProblemDetail onMalformedBody(HttpMessageNotReadableException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.BAD_REQUEST, "Request body could not be parsed");
        pd.setTitle("Malformed request");
        pd.setType(MALFORMED_TYPE);
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
        String limiterName = extractLimiterName(ex.getMessage());
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
