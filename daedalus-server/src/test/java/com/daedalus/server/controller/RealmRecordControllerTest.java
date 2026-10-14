package com.daedalus.server.controller;

import com.daedalus.server.service.RealmRecordService;
import com.daedalus.world.persistence.RealmRecordStore;
import jakarta.servlet.http.HttpServletRequest;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.web.server.ResponseStatusException;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

class RealmRecordControllerTest {
    @Test void updatedAndReplayRepliesRetainExactLargeRevisionHeaders() throws Exception {
        var service = mock(RealmRecordService.class);
        var controller = new RealmRecordController(service, "world-host");
        long expected = 9007199254740992L;
        var stored = new RealmRecordStore.Stored("WORLD-ZERO", "ledger", expected + 1, new byte[] {1}, "a".repeat(64));
        for (var result : List.of(RealmRecordStore.WriteResult.UPDATED, RealmRecordStore.WriteResult.REPLAY)) {
            when(service.compareAndSet(eq("WORLD-ZERO"), eq("ledger"), eq(expected), any(byte[].class)))
                    .thenReturn(new RealmRecordStore.Write(result, stored));
            var request = new MockHttpServletRequest();request.setContent(new byte[] {1});
            var reply = controller.write("WORLD-ZERO", "ledger", expected, request,
                    UsernamePasswordAuthenticationToken.authenticated("world-host", "unused", List.of()));
            assertThat(reply.getStatusCode()).isEqualTo(HttpStatus.OK);
            assertThat(reply.getHeaders().getFirst("X-Record-Revision")).isEqualTo("9007199254740993");
            assertThat(reply.getHeaders().getFirst("X-Payload-SHA256")).isEqualTo(stored.sha256());
            assertThat(reply.getBody().revision()).isEqualTo(expected + 1);
            assertThat(reply.getBody().result()).isEqualTo(result.name());
        }
    }

    @Test void conflictStillDescribesCurrentRecordWithoutSuccessStatus() throws Exception {
        var service = mock(RealmRecordService.class);
        var stored = new RealmRecordStore.Stored("WORLD-ZERO", "ledger", 7, new byte[] {1}, "b".repeat(64));
        when(service.compareAndSet(eq("WORLD-ZERO"), eq("ledger"), eq(0L), any(byte[].class)))
                .thenReturn(new RealmRecordStore.Write(RealmRecordStore.WriteResult.CONFLICT, stored));
        var request = new MockHttpServletRequest();request.setContent(new byte[] {2});
        var reply = new RealmRecordController(service, "world-host").write("WORLD-ZERO", "ledger", 0, request,
                UsernamePasswordAuthenticationToken.authenticated("world-host", "unused", List.of()));
        assertThat(reply.getStatusCode()).isEqualTo(HttpStatus.CONFLICT);
        assertThat(reply.getHeaders().getFirst("X-Record-Revision")).isEqualTo("7");
        assertThat(reply.getBody().result()).isEqualTo("CONFLICT");
    }

    @Test void wrongHostIsRejectedBeforeReadingThePayload() {
        var service = mock(RealmRecordService.class);
        var request = mock(HttpServletRequest.class);
        var controller = new RealmRecordController(service, "world-host");
        assertThatThrownBy(() -> controller.write("WORLD-ZERO", "ledger", 0, request,
                UsernamePasswordAuthenticationToken.authenticated("player", "unused", List.of())))
                .isInstanceOfSatisfying(ResponseStatusException.class,
                        failure -> assertThat(failure.getStatusCode()).isEqualTo(HttpStatus.FORBIDDEN));
        verifyNoInteractions(service, request);
    }
}
