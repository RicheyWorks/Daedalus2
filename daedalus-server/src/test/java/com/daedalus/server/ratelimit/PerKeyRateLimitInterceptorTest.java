// SPDX-License-Identifier: MIT

package com.daedalus.server.ratelimit;

import com.daedalus.server.config.RateLimitProperties;
import io.github.resilience4j.ratelimiter.RateLimiterConfig;
import io.github.resilience4j.ratelimiter.RateLimiterRegistry;
import io.github.resilience4j.ratelimiter.RequestNotPermitted;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.web.method.HandlerMethod;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Unit test of {@link PerKeyRateLimitInterceptor#preHandle}: the throttling decision itself,
 * exercised directly (no DispatcherServlet). Proves each caller key gets an independent bucket
 * cloned from the base instance's config, and that exhaustion raises the standard
 * {@link RequestNotPermitted} carrying the composite instance name.
 */
class PerKeyRateLimitInterceptorTest {

    /** Two permits per (long) refresh window makes exhaustion deterministic within a test. */
    private static final RateLimiterConfig TWO_PER_MINUTE = RateLimiterConfig.custom()
            .limitForPeriod(2)
            .limitRefreshPeriod(Duration.ofMinutes(1))
            .timeoutDuration(Duration.ZERO)
            .build();

    private RateLimiterRegistry registry;
    private PerKeyRateLimitInterceptor interceptor;

    /** Test handlers — one throttled, one not. */
    static class Handlers {
        @PerKeyRateLimit("mazeGenerate")
        public void limited() {
        }

        public void unlimited() {
        }
    }

    private HandlerMethod limited;
    private HandlerMethod unlimited;

    @BeforeEach
    void setUp() throws NoSuchMethodException {
        registry = RateLimiterRegistry.ofDefaults();
        registry.rateLimiter("mazeGenerate", TWO_PER_MINUTE); // the base template
        interceptor = new PerKeyRateLimitInterceptor(registry, new RateLimitKeyResolver(new RateLimitProperties(false)));

        Handlers bean = new Handlers();
        limited = new HandlerMethod(bean, Handlers.class.getMethod("limited"));
        unlimited = new HandlerMethod(bean, Handlers.class.getMethod("unlimited"));
    }

    private MockHttpServletRequest requestFrom(String ip) {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRemoteAddr(ip);
        return request;
    }

    private boolean preHandle(MockHttpServletRequest request, Object handler) {
        return interceptor.preHandle(request, new MockHttpServletResponse(), handler);
    }

    @Test
    void nonHandlerMethod_passesThrough() {
        assertThat(preHandle(requestFrom("1.1.1.1"), "not-a-handler-method")).isTrue();
    }

    @Test
    void methodWithoutAnnotation_isNeverThrottled() {
        MockHttpServletRequest request = requestFrom("1.1.1.1");
        for (int i = 0; i < 50; i++) {
            assertThat(preHandle(request, unlimited)).isTrue();
        }
    }

    @Test
    void sameKey_isThrottledAfterItsBudgetIsSpent() {
        MockHttpServletRequest request = requestFrom("1.1.1.1");

        assertThat(preHandle(request, limited)).isTrue();  // 1st permit
        assertThat(preHandle(request, limited)).isTrue();  // 2nd permit

        assertThatThrownBy(() -> preHandle(request, limited))
                .isInstanceOf(RequestNotPermitted.class)
                // the composite name is carried on the exception; the handler collapses it to the base
                .hasMessageContaining("mazeGenerate::ip:1.1.1.1");
    }

    @Test
    void differentKeys_haveIndependentBuckets() {
        MockHttpServletRequest alice = requestFrom("1.1.1.1");
        // Spend alice's whole budget.
        preHandle(alice, limited);
        preHandle(alice, limited);
        assertThatThrownBy(() -> preHandle(alice, limited)).isInstanceOf(RequestNotPermitted.class);

        // A different IP is unaffected — its own fresh bucket.
        MockHttpServletRequest bob = requestFrom("2.2.2.2");
        assertThatCode(() -> preHandle(bob, limited)).doesNotThrowAnyException();
        assertThat(preHandle(requestFrom("2.2.2.2"), limited)).isTrue(); // still has its 2nd permit
    }
}
