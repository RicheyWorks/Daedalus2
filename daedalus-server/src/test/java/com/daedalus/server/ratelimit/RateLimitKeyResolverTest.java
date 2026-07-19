// SPDX-License-Identifier: MIT

package com.daedalus.server.ratelimit;

import com.daedalus.server.config.RateLimitProperties;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@link RateLimitKeyResolver} decides <em>whose</em> bucket a request draws from. The two axes
 * are: authenticated subject vs. anonymous/none (→ IP), and — for the IP path — whether
 * {@code X-Forwarded-For} is trusted.
 */
class RateLimitKeyResolverTest {

    private final RateLimitKeyResolver trusting = new RateLimitKeyResolver(new RateLimitProperties(true));
    private final RateLimitKeyResolver notTrusting = new RateLimitKeyResolver(new RateLimitProperties(false));

    @AfterEach
    void clearContext() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void authenticatedSubject_keysBySubject() {
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken(
                        "alice", "creds", List.of(new SimpleGrantedAuthority("ROLE_USER"))));

        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRemoteAddr("10.0.0.5"); // present, but must be ignored in favor of the subject

        assertThat(notTrusting.resolve(request)).isEqualTo("sub:alice");
    }

    @Test
    void anonymousAuthentication_fallsThroughToIp() {
        SecurityContextHolder.getContext().setAuthentication(
                new AnonymousAuthenticationToken(
                        "key", "anonymousUser", List.of(new SimpleGrantedAuthority("ROLE_ANONYMOUS"))));

        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRemoteAddr("10.0.0.5");

        assertThat(notTrusting.resolve(request)).isEqualTo("ip:10.0.0.5");
    }

    @Test
    void noAuthentication_keysByRemoteAddr() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRemoteAddr("198.51.100.9");

        assertThat(notTrusting.resolve(request)).isEqualTo("ip:198.51.100.9");
    }

    @Test
    void trustedForwardedHeader_usesFirstHop() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRemoteAddr("10.0.0.1"); // the proxy's address
        request.addHeader("X-Forwarded-For", "203.0.113.7, 70.41.3.18, 10.0.0.1");

        assertThat(trusting.resolve(request)).isEqualTo("ip:203.0.113.7");
    }

    @Test
    void untrustedForwardedHeader_ignoresItAndUsesRemoteAddr() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRemoteAddr("10.0.0.1");
        request.addHeader("X-Forwarded-For", "203.0.113.7"); // spoofable — must be ignored

        assertThat(notTrusting.resolve(request)).isEqualTo("ip:10.0.0.1");
    }

    @Test
    void trustedForwardedHeader_butAbsent_fallsBackToRemoteAddr() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRemoteAddr("10.0.0.1");

        assertThat(trusting.resolve(request)).isEqualTo("ip:10.0.0.1");
    }
}
