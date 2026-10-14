// SPDX-License-Identifier: MIT
package com.daedalus.server.controller;

import com.daedalus.server.service.RealmRecordService;
import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.world.persistence.RealmRecordStore;
import jakarta.servlet.http.HttpServletRequest;
import java.io.IOException;
import java.util.Arrays;
import java.util.Set;
import java.util.stream.Collectors;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

/** Host-only opaque snapshot transport. Does not let player clients manufacture inventories or rescue records. */
@RestController
@RequestMapping("/api/v1/host/realm-records")
@ConditionalOnProperty(name = "daedalus.realm-record.enabled", havingValue = "true")
public class RealmRecordController {
    private final RealmRecordService records;
    private final Set<String> hostSubjects;
    public RealmRecordController(RealmRecordService records,
            @Value("${daedalus.realm-record.host-subjects:}") String subjects) {
        this.records = records;
        hostSubjects = Arrays.stream(subjects.split(",")).map(String::trim).filter(s -> !s.isEmpty()).collect(Collectors.toUnmodifiableSet());
    }
    private void host(Authentication auth) {
        if (auth == null || !auth.isAuthenticated() || auth instanceof AnonymousAuthenticationToken)
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Authenticated world host required");
        // Existing login JWTs carry subjects, not a host-role claim. The operator explicitly selects trusted host subjects.
        if (!hostSubjects.contains(auth.getName()))
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Configured world host required");
    }
    @GetMapping(value = "/{realm}/{key}", produces = MediaType.APPLICATION_OCTET_STREAM_VALUE)
    @PerKeyRateLimit("realmRecords")
    public ResponseEntity<byte[]> read(@PathVariable String realm, @PathVariable String key, Authentication auth) {
        host(auth);
        try {
            var record = records.read(realm, key).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "No stored realm record"));
            return ResponseEntity.ok().contentType(MediaType.APPLICATION_OCTET_STREAM).eTag("\"" + record.revision() + "\"")
                    .header("X-Record-Revision", Long.toString(record.revision())).header("X-Payload-SHA256", record.sha256()).body(record.payload());
        } catch (IllegalArgumentException bad) { throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid record identity", bad); }
        catch (IOException unavailable) { throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "Realm record unavailable", unavailable); }
    }
    public record WriteReply(String result, String realm, String key, long revision, String sha256) {}
    @PutMapping(value = "/{realm}/{key}", consumes = MediaType.APPLICATION_OCTET_STREAM_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    @PerKeyRateLimit("realmRecords")
    public ResponseEntity<WriteReply> write(@PathVariable String realm, @PathVariable String key,
            @RequestHeader("X-Expected-Revision") long expectedRevision, HttpServletRequest request, Authentication auth) {
        host(auth);
        if (expectedRevision < 0 || expectedRevision == Long.MAX_VALUE)
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid expected revision");
        if (request.getContentLengthLong() > RealmRecordStore.MAX_PAYLOAD_BYTES)
            throw new ResponseStatusException(HttpStatus.PAYLOAD_TOO_LARGE, "Snapshot exceeds record limit");
        try {
            // Also bounds chunked requests; authentication happens before payload consumption.
            byte[] payload = request.getInputStream().readNBytes(RealmRecordStore.MAX_PAYLOAD_BYTES + 1);
            if (payload.length > RealmRecordStore.MAX_PAYLOAD_BYTES)
                throw new ResponseStatusException(HttpStatus.PAYLOAD_TOO_LARGE, "Snapshot exceeds record limit");
            var write = records.compareAndSet(realm, key, expectedRevision, payload);var stored = write.record();
            var status = write.result() == RealmRecordStore.WriteResult.CONFLICT ? HttpStatus.CONFLICT : HttpStatus.OK;
            var response = ResponseEntity.status(status);
            // Native consumers can parse the exact decimal revision without JSON double rounding.
            // Conflict headers describe the current record, never confirm the candidate write.
            if (stored != null) response.header("X-Record-Revision", Long.toString(stored.revision()))
                    .header("X-Payload-SHA256", stored.sha256());
            return response.body(new WriteReply(write.result().name(), realm, key,
                    stored == null ? 0 : stored.revision(), stored == null ? null : stored.sha256()));
        } catch (IllegalArgumentException bad) { throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid record update", bad); }
        catch (IOException unavailable) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "Realm record write outcome requires reconciliation", unavailable);
        }
    }
}
