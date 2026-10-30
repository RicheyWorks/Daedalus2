// SPDX-License-Identifier: MIT

package com.daedalus.server.security;

import org.junit.jupiter.api.Test;
import org.springframework.messaging.Message;
import org.springframework.messaging.simp.stomp.StompCommand;
import org.springframework.messaging.simp.stomp.StompHeaderAccessor;
import org.springframework.messaging.support.MessageBuilder;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.assertThatCode;

/**
 * Client {@code SEND} frames are refused, and the reason the refusal is total stays true.
 *
 * <h3>The hole</h3>
 *
 * <p>Two interceptors guarded this channel: one authenticating {@code CONNECT}, one authorising
 * {@code SUBSCRIBE} to an owned session's player topic. Neither looked at {@code SEND}, and the
 * broker is Spring's simple broker with {@code /topic} enabled — so a client frame addressed to
 * a {@code /topic} destination never reaches application code at all. The broker relays it.
 *
 * <p>Driven against a running server before the fix: a second, anonymous client sent one frame
 * to another player's {@code /topic/session/&#123;id&#125;/player} and the spectator received
 * it, indistinguishable from a server-published move.
 *
 * <p>What makes it worth writing down is <em>why</em> it was missed. {@code WebSocketConfig}'s
 * own Javadoc said, in as many words, "do not read their presence as evidence that a client can
 * send frames today" — a reassurance, written after checking that no {@code @MessageMapping}
 * exists. That check was correct and the conclusion did not follow: no mapping proves no code
 * <em>of ours</em> handles a client frame, not that the frame goes nowhere. The simple broker is
 * application code somebody else wrote, and it was listening.
 *
 * <p>Note also which direction had all the attention. Considerable design went into who may
 * <em>read</em> an owned session's feed. Nobody asked who may <em>write</em> to it. From outside,
 * a guard on one direction of a channel looks exactly like a guard on the channel.
 */
class StompSendRejectionTest {

    private final StompSendRejectionInterceptor interceptor = new StompSendRejectionInterceptor();

    private Message<byte[]> frame(StompCommand command, String destination) {
        StompHeaderAccessor accessor = StompHeaderAccessor.create(command);
        if (destination != null) {
            accessor.setDestination(destination);
        }
        accessor.setLeaveMutable(true);
        return MessageBuilder.createMessage(new byte[0], accessor.getMessageHeaders());
    }

    @Test
    void aClientSendIsRefusedWhereverItIsAddressed() {
        // Every destination family the application uses, plus the /app prefix that is configured
        // but has no handler behind it. None of them is a legitimate client SEND target.
        List<String> destinations = List.of(
                "/topic/session/11111111-2222-3333-4444-555555555555/player",
                "/topic/maze/11111111-2222-3333-4444-555555555555/state",
                "/topic/maze/11111111-2222-3333-4444-555555555555/solver",
                "/topic/plugins/failures",
                "/queue/anything",
                "/app/maze/move",
                "/user/queue/private");

        for (String destination : destinations) {
            assertThatThrownBy(() -> interceptor.preSend(frame(StompCommand.SEND, destination),
                    null))
                    .as("SEND to %s must be refused", destination)
                    .isInstanceOf(IllegalStateException.class)
                    .hasMessageContaining("broadcast-only");
        }
        // A SEND with no destination at all is still a SEND.
        assertThatThrownBy(() -> interceptor.preSend(frame(StompCommand.SEND, null), null))
                .isInstanceOf(IllegalStateException.class);
    }

    @Test
    void everyOtherCommandPassesThroughUntouched() {
        // A rejection interceptor that also breaks CONNECT or SUBSCRIBE would take the whole
        // WebSocket surface down with it, and the suite would still be green on the SEND case.
        for (StompCommand command : List.of(StompCommand.CONNECT, StompCommand.CONNECTED,
                StompCommand.SUBSCRIBE, StompCommand.UNSUBSCRIBE, StompCommand.DISCONNECT,
                StompCommand.ACK, StompCommand.NACK, StompCommand.BEGIN, StompCommand.COMMIT,
                StompCommand.ABORT, StompCommand.MESSAGE, StompCommand.RECEIPT,
                StompCommand.ERROR)) {
            Message<byte[]> message = frame(command, "/topic/whatever");
            assertThatCode(() -> interceptor.preSend(message, null))
                    .as("%s must pass through", command).doesNotThrowAnyException();
            assertThat(interceptor.preSend(message, null))
                    .as("%s must be returned unchanged", command).isSameAs(message);
        }
    }

    @Test
    void aMessageWithNoStompAccessorPassesThrough() {
        // Heart-beats and non-STOMP traffic on the same channel carry no accessor. Throwing on
        // them would turn a keepalive into a disconnect.
        Message<byte[]> plain = MessageBuilder.withPayload(new byte[0]).build();
        assertThat(interceptor.preSend(plain, null)).isSameAs(plain);
    }

    @Test
    void theBlanketRuleStaysCorrectOnlyWhileNothingHandlesClientMessages() throws IOException {
        // The refusal is total because this application has nothing for a client to say. That is
        // a fact about the codebase, not a principle, so it is checked rather than asserted in
        // prose. The day someone adds a @MessageMapping, refusing every SEND silently breaks
        // their feature — this fails the build first and points at the interceptor.
        // Anchored to the start of a line, so it finds annotations on declarations and not the
        // several places this codebase *discusses* them — including the paragraph above. The
        // first version of this scan matched its own Javadoc and reported three handlers in two
        // files that contain no code at all, which is a good argument for running a scanner
        // once against a tree you already know the answer for.
        Pattern declaration = Pattern.compile(
                "^\\s*@(MessageMapping|SubscribeMapping|MessageExceptionHandler)\\b",
                Pattern.MULTILINE);

        // Positive control. This assertion is about an absence, and an absence is what a broken
        // scanner reports too — narrow the pattern to nothing and the sweep below comes back
        // clean and confident. So prove the pattern can still find what it is looking for, and
        // that it still ignores the prose above.
        assertThat(declaration.matcher("    @MessageMapping(\"/maze/move\")").find())
                .as("the scanner must match a real declaration").isTrue();
        assertThat(declaration.matcher(" * mentions @MessageMapping in a comment").find())
                .as("the scanner must not match prose").isFalse();

        var mappings = new ArrayList<String>();
        Path root = Path.of("src/main/java");
        try (Stream<Path> files = Files.walk(root)) {
            for (Path file : files.filter(f -> f.toString().endsWith(".java")).toList()) {
                Matcher m = declaration.matcher(Files.readString(file));
                while (m.find()) {
                    mappings.add(file.getFileName() + " declares @" + m.group(1));
                }
            }
        }
        assertThat(mappings)
                .as("StompSendRejectionInterceptor refuses ALL client SEND frames, which is only "
                        + "the right rule while no handler wants one. Something now does: %s. "
                        + "Narrow the interceptor to the destinations that are still not "
                        + "client-writable, and give the new handler its own authorization.",
                        mappings)
                .isEmpty();
    }
}
