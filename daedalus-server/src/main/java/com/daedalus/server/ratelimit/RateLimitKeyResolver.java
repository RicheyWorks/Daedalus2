// SPDX-License-Identifier: MIT

package com.daedalus.server.ratelimit;

import com.daedalus.server.config.RateLimitProperties;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;

/**
 * Resolves the throttling key for an incoming request: <em>who</em> a per-key rate-limit bucket
 * belongs to.
 *
 * <p>Resolution order:
 * <ol>
 *   <li><b>Authenticated subject.</b> If the security context holds a real (non-anonymous)
 *       authentication with a non-blank name, the key is {@code sub:<name>}. On the protected
 *       prod surface this means each JWT subject gets its own bucket, so one noisy client can't
 *       spend another's quota.</li>
 *   <li><b>Client IP.</b> Otherwise the key is {@code ip:<address>}. This is the path taken by
 *       {@code /auth/login} (unauthenticated by nature — it's how you get a token) and by the
 *       whole surface in the dev profile, where everything is anonymous. When
 *       {@link RateLimitProperties#trustForwardedHeader()} is set <em>and</em> an
 *       {@code X-Forwarded-For} header is present, the first hop (original client) is used;
 *       otherwise the socket {@code remoteAddr}.</li>
 * </ol>
 *
 * <p>The {@code sub:} / {@code ip:} prefixes keep the two key spaces disjoint, so a subject named
 * after an IP literal can never collide with that IP's bucket.
 */
@Component
public class RateLimitKeyResolver {

    private static final String ANONYMOUS_KEY = "ip:unknown";

    private final RateLimitProperties properties;

    public RateLimitKeyResolver(RateLimitProperties properties) {
        this.properties = properties;
    }

    /**
     * Compute the caller key for {@code request}. Never returns {@code null}; falls back to
     * {@code ip:unknown} if neither a subject nor any address can be determined.
     */
    public String resolve(HttpServletRequest request) {
        String subject = authenticatedSubject();
        if (subject != null) {
            return "sub:" + subject;
        }
        return "ip:" + clientIp(request);
    }

    /**
     * The authenticated subject name, or {@code null} when the request is unauthenticated or
     * anonymous. Anonymous authentication (Spring Security's default for permit-all requests) is
     * explicitly excluded so it doesn't collapse every dev-profile caller into one shared bucket.
     */
    private static String authenticatedSubject() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || !auth.isAuthenticated() || auth instanceof AnonymousAuthenticationToken) {
            return null;
        }
        String name = auth.getName();
        return (name == null || name.isBlank()) ? null : name;
    }

    /**
     * Best-effort client IP. Honors {@code X-Forwarded-For} only when configured to trust it
     * (i.e. a known proxy sets it) — see {@link RateLimitProperties#trustForwardedHeader()}.
     */
    private String clientIp(HttpServletRequest request) {
        if (properties.trustForwardedHeader()) {
            String forwarded = request.getHeader("X-Forwarded-For");
            if (forwarded != null && !forwarded.isBlank()) {
                // XFF is a comma-separated chain; the first entry is the original client.
                int comma = forwarded.indexOf(',');
                String first = (comma < 0 ? forwarded : forwarded.substring(0, comma)).trim();
                if (!first.isEmpty()) {
                    return first;
                }
            }
        }
        String remote = request.getRemoteAddr();
        if (remote == null || remote.isBlank()) {
            return ANONYMOUS_KEY.substring("ip:".length());
        }
        return remote;
    }
}
