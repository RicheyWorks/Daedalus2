// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.GenericJacksonJsonRedisSerializer;
import org.springframework.data.redis.serializer.StringRedisSerializer;
import tools.jackson.databind.jsontype.BasicPolymorphicTypeValidator;
import tools.jackson.databind.jsontype.PolymorphicTypeValidator;

/**
 * Redis configuration. Used by {@code LeaderboardService} (sorted sets) and the replay store.
 *
 * <p>If Redis is unavailable in dev, set {@code daedalus.redis.enabled=false} in application.yml
 * and services will fall back to in-memory caches.
 *
 * <h3>Why the serializer is configured rather than defaulted</h3>
 *
 * <p>Values go into Redis as {@code Object} and come back as {@code Object}, so a payload has to
 * carry its own type or nothing can be reconstructed from it. Spring Data's stock
 * {@link GenericJacksonJsonRedisSerializer} writes no type information at all: a
 * {@code LeaderboardEntry} comes back through it as a {@code LinkedHashMap}, which
 * {@code LeaderboardService}'s {@code instanceof LeaderboardEntry} filter drops on the floor.
 * Default typing — a {@code @class} property naming the concrete type — is therefore not a
 * nicety here, it is what makes the backend work at all.
 *
 * <p>Enabling it demands a {@link PolymorphicTypeValidator}, because "instantiate whichever class
 * this payload names" is the shape of every JSON deserialization gadget attack. The validator
 * below is the allow-list; anything else appearing in a {@code @class} is refused at read time,
 * however it got into Redis.
 */
@Configuration
@ConditionalOnProperty(prefix = "daedalus.redis", name = "enabled", havingValue = "true")
public class RedisConfig {

    @Bean
    public RedisConnectionFactory redisConnectionFactory() {
        // Pulls from spring.data.redis.* in application.yml
        return new LettuceConnectionFactory();
    }

    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory cf) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(cf);
        template.setKeySerializer(new StringRedisSerializer());
        template.setHashKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(jsonSerializer());
        template.setHashValueSerializer(jsonSerializer());
        template.afterPropertiesSet();
        return template;
    }

    /**
     * The allow-list for {@code @class}. Deliberately narrow: the types this application stores
     * ({@code com.daedalus.*}) and the collection types a template typed {@code <String, Object>}
     * may legitimately wrap them in. {@code java.time} and {@code UUID} need no entry — they are
     * final, so Jackson inlines them with no type id to validate.
     */
    static PolymorphicTypeValidator typeValidator() {
        return BasicPolymorphicTypeValidator.builder()
                .allowIfSubType("com.daedalus.")
                .allowIfSubType("java.util.")
                .build();
    }

    /**
     * Package-private so {@code RedisSerializationRoundTripTest} can exercise the real thing
     * rather than a rebuilt lookalike — a serializer test that configures its own serializer
     * proves only that Jackson works.
     */
    static GenericJacksonJsonRedisSerializer jsonSerializer() {
        return GenericJacksonJsonRedisSerializer.builder()
                .enableDefaultTyping(typeValidator())
                .build();
    }
}
