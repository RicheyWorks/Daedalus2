// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import org.junit.jupiter.api.Test;
import org.springframework.boot.autoconfigure.AutoConfigurations;
import org.springframework.boot.autoconfigure.data.redis.RedisAutoConfiguration;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Locks in the audit's #3 server fix: {@link RedisConfig} must only contribute its Lettuce
 * connection factory + {@code RedisTemplate} beans when {@code daedalus.redis.enabled=true}.
 *
 * <p>Without the conditional, Spring Boot tries to dial Redis on every startup — including
 * dev profiles that explicitly opt out via {@code application-dev.yml}. The
 * {@code @ConditionalOnProperty} annotation we just added is what makes those dev runs viable.
 */
class RedisConfigConditionalTest {

    /**
     * Runner pulls in only the user-supplied {@link RedisConfig} plus Spring Boot's stock
     * {@link RedisAutoConfiguration}. We toggle the flag and assert what gets wired.
     */
    private final ApplicationContextRunner runner = new ApplicationContextRunner()
            .withConfiguration(AutoConfigurations.of(RedisAutoConfiguration.class))
            .withUserConfiguration(RedisConfig.class);

    @Test
    void whenRedisDisabled_redisConfigBeansAreAbsent() {
        runner.withPropertyValues("daedalus.redis.enabled=false")
                .run(ctx -> {
                    // The conditional should suppress the @Configuration class entirely.
                    assertThat(ctx).doesNotHaveBean(RedisConfig.class);

                    // Spring Boot's RedisAutoConfiguration may still register a default
                    // RedisConnectionFactory bean — that's fine and unrelated to our fix. The
                    // contract we lock in here is "RedisConfig itself is gated".
                });
    }

    @Test
    void whenRedisEnabled_redisConfigBeansArePresent() {
        runner.withPropertyValues(
                        "daedalus.redis.enabled=true",
                        // Point at a port that is almost certainly closed locally; we never
                        // open a connection, we just verify that the beans are *defined*.
                        "spring.data.redis.host=127.0.0.1",
                        "spring.data.redis.port=63799")
                .run(ctx -> {
                    assertThat(ctx).hasSingleBean(RedisConfig.class);
                    assertThat(ctx).hasBean("redisConnectionFactory");
                    assertThat(ctx.getBean(RedisConnectionFactory.class)).isNotNull();
                    assertThat(ctx.getBean("redisTemplate", RedisTemplate.class)).isNotNull();
                });
    }

    @Test
    void whenPropertyAbsent_defaultsToDisabled() {
        // Audit's stated default: "Defaults to false when property is absent → matches
        // LeaderboardService default." Verify that contract holds.
        runner.run(ctx -> assertThat(ctx).doesNotHaveBean(RedisConfig.class));
    }
}
