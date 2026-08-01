// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import com.daedalus.model.LeaderboardEntry;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.serializer.GenericJacksonJsonRedisSerializer;
import org.springframework.data.redis.serializer.SerializationException;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * What {@link RedisConfig}'s serializer writes, it must be able to read.
 *
 * <h3>Why this test exists</h3>
 *
 * <p>Until 2026-07-31 it could not. The template was handed a hand-built {@code ObjectMapper}
 * with {@code activateDefaultTyping(validator, NON_FINAL)}, and the two halves of that disagreed:
 * writing used the value's runtime type, and {@code LeaderboardEntry} is a {@code record} and
 * therefore <em>final</em>, so no type header was emitted — while reading targeted {@code Object},
 * which is non-final, so the deserializer demanded one. Every read threw
 * {@link SerializationException}.
 *
 * <p>The failure was invisible from outside. {@code LeaderboardService} catches read failures and
 * falls back to its in-memory set, so with {@code daedalus.redis.enabled=true} the boards still
 * answered — out of memory, one warn line per call — while every submitted run kept piling
 * unreadable JSON into sorted sets that no code path could ever read back. The Redis backend
 * appeared to work and did nothing.
 *
 * <p>Nothing caught it because the only Redis test asserted that the beans <em>exist</em>.
 * A serializer bean that constructs is not a serializer that works, and the distance between
 * those two claims was this bug's entire hiding place.
 *
 * <h3>Teeth</h3>
 *
 * <p>Replayed against the pre-fix configuration, three of the four assertions below fail: the two
 * round-trip cases with the {@link SerializationException} described above, and the allow-list
 * case because {@code mapper.getPolymorphicTypeValidator()} returns a laissez-faire validator —
 * the old configuration really does construct a {@code javax.naming.InitialContext} named by a
 * Redis payload, which is the JNDI gadget's front door.
 *
 * <p>{@link #aCollectionOfEntriesSurvivesTheRoundTrip()} is the honest exception: it passes on
 * the old configuration too, because {@code ArrayList} is <em>not</em> final, so default typing
 * always wrote a header for it. That is the shape of the bug in one line — it bit exactly the
 * final types, and a test that stored its fixtures in a list would have missed it entirely. The
 * case is kept because it pins something else worth pinning: that the validator's allow-list
 * still covers the collections a {@code <String, Object>} template may wrap values in.
 *
 * <p>All four call {@link RedisConfig}'s own factory method rather than building a serializer
 * inline. A serializer test that configures its own serializer proves only that Jackson works,
 * and would have stayed green through the entire outage.
 */
class RedisSerializationRoundTripTest {

    private final GenericJacksonJsonRedisSerializer serializer = RedisConfig.jsonSerializer();

    private static LeaderboardEntry entry() {
        return new LeaderboardEntry(
                UUID.fromString("00000000-0000-0000-0000-0000000000a1"),
                UUID.fromString("00000000-0000-0000-0000-0000000000b2"),
                "ariadne", 4200L, 137L, 9876L, "recursive-backtracker",
                Instant.parse("2026-07-31T12:00:00Z"));
    }

    @Test
    void aLeaderboardEntrySurvivesTheRoundTrip() {
        Object back = serializer.deserialize(serializer.serialize(entry()));

        assertThat(back)
                .as("a value written by this serializer must come back as the type it went in as "
                        + "— LeaderboardService's `instanceof LeaderboardEntry` filter discards "
                        + "anything else, so a Map here means an empty leaderboard")
                .isInstanceOf(LeaderboardEntry.class)
                .isEqualTo(entry());
    }

    @Test
    void theInstantSurvivesToTheNanosecond() {
        // Timestamps are the field most likely to drift silently across a serializer change:
        // Jackson 2 wrote epoch decimals, Jackson 3 writes ISO-8601, and both parse back to the
        // same Instant. Equality above would catch a lossy conversion, but only if this field is
        // exercised with a value whose sub-second part is non-zero.
        LeaderboardEntry precise = new LeaderboardEntry(
                UUID.randomUUID(), UUID.randomUUID(), "theseus", 1L, 2L, 3L, "wilson",
                Instant.parse("2026-07-31T12:00:00.123456789Z"));

        Object back = serializer.deserialize(serializer.serialize(precise));

        assertThat(((LeaderboardEntry) back).achievedAt())
                .isEqualTo(Instant.parse("2026-07-31T12:00:00.123456789Z"));
    }

    @Test
    void aCollectionOfEntriesSurvivesTheRoundTrip() {
        // The template is typed <String, Object>; nothing stops a caller storing a list, and a
        // validator that allowed only com.daedalus.* would refuse the ArrayList wrapping them.
        List<LeaderboardEntry> many = new ArrayList<>(List.of(entry(), entry()));

        Object back = serializer.deserialize(serializer.serialize(many));

        assertThat(back).isEqualTo(many);
    }

    @Test
    void aClassOutsideTheAllowListIsRefused() {
        // The security half of default typing: the reader instantiates whatever @class names, so
        // the validator is the only thing standing between a writable Redis and arbitrary
        // construction. Not a hypothetical — it is the entire JSON deserialization gadget genre.
        byte[] forged = "{\"@class\":\"javax.naming.InitialContext\"}".getBytes();

        assertThatThrownBy(() -> serializer.deserialize(forged))
                .as("a @class outside the allow-list must be refused, not constructed")
                .isInstanceOf(SerializationException.class);
    }
}
