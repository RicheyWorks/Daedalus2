// SPDX-License-Identifier: MIT

package com.daedalus.server.ratelimit;

import com.daedalus.server.config.RateLimitProperties;
import com.github.benmanes.caffeine.cache.Ticker;
import io.github.resilience4j.ratelimiter.RateLimiterConfig;
import io.github.resilience4j.ratelimiter.RateLimiterRegistry;
import io.github.resilience4j.ratelimiter.RequestNotPermitted;
import jakarta.servlet.http.HttpServletRequest;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.web.method.HandlerMethod;

import java.lang.reflect.Method;
import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The per-key bucket store is bounded, and bounding it must not create a way around the limit.
 *
 * <p>Buckets used to accumulate in the {@link RateLimiterRegistry} forever, so a caller minting
 * distinct keys could grow it without limit. Capping the store fixes that but introduces the
 * opposite hazard: discarding a bucket someone has already drained gives them a fresh budget.
 * These tests pin both halves — memory is bounded, and eviction never refunds permits early.
 */
class PerKeyRateLimitEvictionTest {

    /** A handler carrying {@code @PerKeyRateLimit("test")}, for the interceptor to find. */
    @SuppressWarnings("unused")
    static class Controller {
        @PerKeyRateLimit("test")
        public void limited() {
        }
    }

    private static HandlerMethod handler() throws NoSuchMethodException {
        Method method = Controller.class.getMethod("limited");
        return new HandlerMethod(new Controller(), method);
    }

    private static RateLimiterRegistry registryWith(int permits, Duration refresh) {
        return RateLimiterRegistry.of(RateLimiterConfig.custom()
                .limitForPeriod(permits)
                .limitRefreshPeriod(refresh)
                .timeoutDuration(Duration.ZERO)
                .build());
    }

    private static HttpServletRequest fromIp(String ip) {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRemoteAddr(ip);
        return request;
    }

    /** A hand-cranked clock, so expiry is asserted exactly instead of slept for. */
    static final class FakeClock implements Ticker {
        private long nanos;

        @Override
        public long read() {
            return nanos;
        }

        void advance(Duration by) {
            nanos += by.toNanos();
        }
    }

    private static PerKeyRateLimitInterceptor interceptor(RateLimiterRegistry registry,
                                                          int maxKeys, Duration idleTtl) {
        return interceptor(registry, maxKeys, idleTtl, new FakeClock());
    }

    private static PerKeyRateLimitInterceptor interceptor(RateLimiterRegistry registry, int maxKeys,
                                                          Duration idleTtl, Ticker ticker) {
        return new PerKeyRateLimitInterceptor(registry,
                new RateLimitKeyResolver(new RateLimitProperties(false)), maxKeys, idleTtl, ticker);
    }

    @Test
    void bucketCountIsCappedNoMatterHowManyDistinctCallersArrive() throws Exception {
        // The leak this replaces: 500 distinct source IPs used to mean 500 permanent registry
        // entries. The cap is what makes a key-flood a bounded cost.
        PerKeyRateLimitInterceptor subject =
                interceptor(registryWith(1_000, Duration.ofSeconds(1)), 50, Duration.ofMinutes(10));

        for (int i = 0; i < 500; i++) {
            subject.preHandle(fromIp("10.0." + (i / 256) + "." + (i % 256)), null, handler());
        }

        assertThat(subject.trackedKeyCount())
                .as("bucket store must respect its ceiling under a key flood")
                .isLessThanOrEqualTo(50);
    }

    @Test
    void separateCallersStillGetSeparateBudgets() throws Exception {
        // The property the whole feature exists for — bounding storage must not merge callers.
        PerKeyRateLimitInterceptor subject =
                interceptor(registryWith(1, Duration.ofMinutes(5)), 1_000, Duration.ofMinutes(10));

        subject.preHandle(fromIp("10.0.0.1"), null, handler());
        assertThatThrownBy(() -> subject.preHandle(fromIp("10.0.0.1"), null, handler()))
                .as("second call from the same IP exhausts that IP's single permit")
                .isInstanceOf(RequestNotPermitted.class);

        // A different caller is unaffected.
        assertThat(subject.preHandle(fromIp("10.0.0.2"), null, handler())).isTrue();
    }

    @Test
    void aDrainedBucketIsNotEvictedBeforeItWouldHaveRefilled() throws Exception {
        // The bypass this design has to avoid. idleTtl is deliberately far shorter than the
        // refresh period; the effective TTL must be raised to the refresh period, so the
        // drained bucket survives and the caller stays throttled.
        FakeClock clock = new FakeClock();
        PerKeyRateLimitInterceptor subject = interceptor(
                registryWith(1, Duration.ofMinutes(30)),   // refills only every 30 minutes
                1_000,
                Duration.ofNanos(1),                       // "evict almost immediately"
                clock);

        subject.preHandle(fromIp("10.0.0.7"), null, handler());
        clock.advance(Duration.ofMinutes(5)); // way past the 1ns idle TTL, far short of 30 min

        assertThatThrownBy(() -> subject.preHandle(fromIp("10.0.0.7"), null, handler()))
                .as("a short idle TTL must not hand back permits the refresh period still owes")
                .isInstanceOf(RequestNotPermitted.class);
    }

    @Test
    void anIdleBucketIsEventuallyReclaimed() throws Exception {
        // The other side of the same rule: once the refresh period has passed the bucket would
        // have refilled anyway, so dropping it costs nothing and the memory comes back.
        FakeClock clock = new FakeClock();
        PerKeyRateLimitInterceptor subject = interceptor(
                registryWith(1, Duration.ofMinutes(1)), 1_000, Duration.ofMinutes(1), clock);

        subject.preHandle(fromIp("10.0.0.9"), null, handler());
        assertThat(subject.trackedKeyCount()).isEqualTo(1);

        clock.advance(Duration.ofMinutes(5));

        assertThat(subject.trackedKeyCount())
                .as("an idle bucket past its refresh period should be reclaimed")
                .isZero();
    }

    @Test
    void unannotatedHandlersAndNonHandlerObjectsPassThrough() throws Exception {
        PerKeyRateLimitInterceptor subject =
                interceptor(registryWith(1, Duration.ofMinutes(5)), 10, Duration.ofMinutes(1));

        // A static-resource dispatch is not a HandlerMethod at all.
        assertThat(subject.preHandle(fromIp("10.0.0.1"), null, new Object())).isTrue();
        assertThat(subject.trackedKeyCount())
                .as("nothing should be tracked for requests that are not rate limited")
                .isZero();
    }
}
