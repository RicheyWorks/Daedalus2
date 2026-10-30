// SPDX-License-Identifier: MIT

package com.daedalus.server.ratelimit;

import com.daedalus.server.config.RateLimitProperties;
import com.daedalus.server.web.ApiExceptionHandler;
import io.github.resilience4j.ratelimiter.RateLimiterConfig;
import io.github.resilience4j.ratelimiter.RateLimiterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.RequestPostProcessor;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Duration;

import static org.hamcrest.Matchers.equalTo;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * End-to-end proof through the DispatcherServlet: a {@link PerKeyRateLimit}-annotated endpoint,
 * fronted by {@link PerKeyRateLimitInterceptor} and {@link ApiExceptionHandler}, must
 * <ul>
 *   <li>serve a caller until its per-key budget is spent, then return {@code 429} with an honest
 *       {@code Retry-After} and a {@code problem+json} body whose {@code limiter} is the
 *       <em>base</em> name (no leaked IP);</li>
 *   <li>keep a different caller's bucket independent.</li>
 * </ul>
 * This covers the wiring the direct-{@code preHandle} unit test can't: that an exception thrown
 * in {@code preHandle} is routed to the controller advice and rendered as the 429 contract.
 */
class PerKeyRateLimitMockMvcTest {

    @RestController
    static class RlController {
        @GetMapping("/rl-test")
        @PerKeyRateLimit("mazeGenerate")
        public String ping() {
            return "ok";
        }
    }

    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        // One permit per minute makes the second same-caller request a guaranteed 429.
        RateLimiterConfig onePerMinute = RateLimiterConfig.custom()
                .limitForPeriod(1)
                .limitRefreshPeriod(Duration.ofMinutes(1))
                .timeoutDuration(Duration.ZERO)
                .build();
        RateLimiterRegistry registry = RateLimiterRegistry.ofDefaults();
        registry.rateLimiter("mazeGenerate", onePerMinute);

        PerKeyRateLimitInterceptor interceptor =
                new PerKeyRateLimitInterceptor(registry, new RateLimitKeyResolver(new RateLimitProperties(false)));

        mvc = MockMvcBuilders.standaloneSetup(new RlController())
                .addInterceptors(interceptor)
                .setControllerAdvice(new ApiExceptionHandler(registry))
                .build();
    }

    private static RequestPostProcessor fromIp(String ip) {
        return request -> {
            request.setRemoteAddr(ip);
            return request;
        };
    }

    @Test
    void firstCallSucceeds_secondFromSameIpIs429_withBaseLimiterNameAndRetryAfter() throws Exception {
        mvc.perform(get("/rl-test").with(fromIp("9.9.9.9")))
                .andExpect(status().isOk())
                .andExpect(content().string("ok"));

        mvc.perform(get("/rl-test").with(fromIp("9.9.9.9")))
                .andExpect(status().isTooManyRequests())
                .andExpect(header().string(HttpHeaders.RETRY_AFTER, "60"))
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON))
                // base name only — the caller IP must not leak into the body
                .andExpect(jsonPath("$.limiter", equalTo("mazeGenerate")))
                .andExpect(jsonPath("$.retryAfterSeconds", equalTo(60)));
    }

    @Test
    void aDifferentIpHasItsOwnBudget() throws Exception {
        // Exhaust one caller.
        mvc.perform(get("/rl-test").with(fromIp("9.9.9.9"))).andExpect(status().isOk());
        mvc.perform(get("/rl-test").with(fromIp("9.9.9.9"))).andExpect(status().isTooManyRequests());

        // A different caller is unaffected.
        mvc.perform(get("/rl-test").with(fromIp("8.8.8.8"))).andExpect(status().isOk());
    }
}
