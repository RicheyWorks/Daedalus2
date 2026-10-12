// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.header.writers.DelegatingRequestMatcherHeaderWriter;
import org.springframework.security.web.header.writers.frameoptions.XFrameOptionsHeaderWriter;
import org.springframework.security.web.util.matcher.NegatedRequestMatcher;
import org.springframework.security.web.util.matcher.RequestMatcher;

/**
 * X-Frame-Options stays DENY everywhere except a token's on-chain HTML, which the realm's own jukebox panel
 * frames (SAMEORIGIN, set by the controller). That response also carries {@code CSP: sandbox allow-scripts},
 * so the framed token runs in an opaque origin and cannot reach the realm's sign-in token.
 */
public final class JukeboxFraming {

    static final RequestMatcher TOKEN_HTML = req -> {
        String uri = req.getRequestURI();
        return uri != null && uri.matches("/api/v1/jukebox/tokens/\\d+/html");
    };

    private JukeboxFraming() {}

    public static void apply(HttpSecurity http) throws Exception {
        http.headers(h -> h
                .frameOptions(f -> f.disable())
                .addHeaderWriter(new DelegatingRequestMatcherHeaderWriter(new NegatedRequestMatcher(TOKEN_HTML),
                        new XFrameOptionsHeaderWriter(XFrameOptionsHeaderWriter.XFrameOptionsMode.DENY))));
    }
}
