// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import com.daedalus.server.ratelimit.PerKeyRateLimitInterceptor;
import com.daedalus.server.ratelimit.RateLimitKeyResolver;
import io.github.resilience4j.ratelimiter.RateLimiterRegistry;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Wires {@link PerKeyRateLimitInterceptor} into the MVC handler chain.
 *
 * <p>The interceptor is registered for {@code /api/**} (the REST surface) but only actually
 * throttles handler methods that carry {@code @PerKeyRateLimit}; every other handler passes
 * through untouched, so the path pattern is just an early-exit optimization rather than the
 * policy boundary.
 */
@Configuration
public class RateLimitWebConfig implements WebMvcConfigurer {

    private final PerKeyRateLimitInterceptor interceptor;

    public RateLimitWebConfig(RateLimiterRegistry rateLimiterRegistry, RateLimitKeyResolver keyResolver,
                              RateLimitProperties properties) {
        this.interceptor = new PerKeyRateLimitInterceptor(rateLimiterRegistry, keyResolver,
                properties.maxKeys(), properties.idleTtl());
    }

    @Override
    public void addInterceptors(InterceptorRegistry interceptorRegistry) {
        interceptorRegistry.addInterceptor(interceptor).addPathPatterns("/api/**");
    }
}
