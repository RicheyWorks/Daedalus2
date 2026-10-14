// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import org.junit.jupiter.api.Test;
import org.springframework.boot.autoconfigure.AutoConfigurations;
import org.springframework.boot.data.redis.autoconfigure.DataRedisAutoConfiguration;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The custom {@code RedisTemplate} is opt-in; Boot owns the configured connection factory.
 *
 * <p>Without the conditional, Spring Boot tries to dial Redis on every startup — including
 * dev profiles that explicitly opt out via {@code application-dev.yml}. The
 * {@code @ConditionalOnProperty} annotation we just added is what makes those dev runs viable.
 */
class RedisConfigConditionalTest {

    /**
     * Runner pulls in only the user-supplied {@link RedisConfig} plus Spring Boot's stock
     * {@link DataRedisAutoConfiguration}. We toggle the flag and assert what gets wired.
     *
     * <p>Spring Boot 4 split the monolithic {@code spring-boot-autoconfigure} jar into
     * per-technology modules, which both moved and renamed this class:
     * {@code org.springframework.boot.autoconfigure.data.redis.RedisAutoConfiguration} became
     * {@code org.springframework.boot.data.redis.autoconfigure.DataRedisAutoConfiguration}.
     * This import was the <em>only</em> source change the whole Boot 3 → 4 migration required.
     */
    private final ApplicationContextRunner runner = new ApplicationContextRunner()
            .withConfiguration(AutoConfigurations.of(DataRedisAutoConfiguration.class))
            .withUserConfiguration(RedisConfig.class);

    @Test
    void whenRedisDisabled_redisConfigBeansAreAbsent() {
        runner.withPropertyValues("daedalus.redis.enabled=false")
                .run(ctx -> {
                    // The conditional should suppress the @Configuration class entirely.
                    assertThat(ctx).doesNotHaveBean(RedisConfig.class);

                    // Spring Boot's DataRedisAutoConfiguration may still register a default
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

    @Test
    void configuredConnectionPropertiesAreNotReplacedByLocalhostDefaults() {
        runner.withPropertyValues("daedalus.redis.enabled=true", "spring.data.redis.host=redis-fixture.invalid",
                        "spring.data.redis.port=6388", "spring.data.redis.database=3",
                        "spring.data.redis.username=fixture-user", "spring.data.redis.password=fixture-password",
                        "spring.data.redis.timeout=750ms", "spring.data.redis.connect-timeout=400ms")
                .run(ctx -> {
                    var factory = ctx.getBean(org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory.class);
                    assertThat(factory.getHostName()).isEqualTo("redis-fixture.invalid");
                    assertThat(factory.getPort()).isEqualTo(6388);
                    assertThat(factory.getDatabase()).isEqualTo(3);
                    assertThat(factory.getStandaloneConfiguration().getUsername()).isEqualTo("fixture-user");
                    assertThat(factory.getStandaloneConfiguration().getPassword().isPresent()).isTrue();
                    assertThat(factory.getStandaloneConfiguration().getPassword().get()).containsExactly("fixture-password".toCharArray());
                    assertThat(factory.getClientConfiguration().getCommandTimeout()).isEqualTo(java.time.Duration.ofMillis(750));
                    assertThat(factory.getClientConfiguration().getClientOptions()).isPresent();
                    assertThat(factory.getClientConfiguration().getClientOptions().orElseThrow()
                            .getSocketOptions().getConnectTimeout()).isEqualTo(java.time.Duration.ofMillis(400));
                });
    }

    @Test
    void bootRetainsConfiguredTlsInsteadOfAnUnencryptedDefaultFactory() {
        runner.withPropertyValues("daedalus.redis.enabled=true", "spring.data.redis.ssl.enabled=true")
                .run(ctx -> assertThat(ctx.getBean(org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory.class)
                        .getClientConfiguration().isUseSsl()).isTrue());
    }
}
