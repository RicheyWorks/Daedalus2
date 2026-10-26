// SPDX-License-Identifier: MIT
package com.daedalus.server.service.simulation;

import com.daedalus.server.controller.LivingWorldController;
import com.daedalus.server.web.ApiExceptionHandler;
import com.daedalus.world.WorldId;
import com.daedalus.world.simulation.SimulationCodec;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class LivingWorldServiceTest {
    private static final String ID = "00000000-0000-0000-0000-000000000001";
    @TempDir Path temp;
    private final long[] clock = {1000};
    private LivingWorldService open(SimulationRepository repository, Consumer<LivingWorldService.Update> events) throws IOException {
        return new LivingWorldService(repository, WorldId.ZERO, 0, "alice", 1000, () -> clock[0], events, new SimpleMeterRegistry());
    }
    @Test void restartRecoversQuestMemoryReceiptAndDrySpell() throws IOException {
        Path file = temp.resolve("world.simulation");
        LivingWorldService.View before;
        try (var service = open(new FileSimulationRepository(file), e -> { })) {
            service.supply("world-zero", "alice", ID, 3);
            clock[0] = 26_000;
            service.advance();
            before = service.inspect("world-zero");
            assertTrue(before.drySpell());
        }
        try (var service = open(new FileSimulationRepository(file), e -> { })) {
            assertEquals(before, service.inspect("world-zero"));
            assertTrue(service.supply("world-zero", "alice", ID, 3).duplicate());
            clock[0] = 37_000;
            service.advance();
            assertFalse(service.inspect("world-zero").drySpell());
            assertEquals("alice", service.inspect("world-zero").rememberedActor());
        }
    }
    @Test void failedPersistenceCannotChangeLiveStateOrPublishAndRetryCommitsOnce() throws IOException {
        var repository = new MemoryRepository();
        List<LivingWorldService.Update> published = new ArrayList<>();
        try (var service = open(repository, published::add)) {
            var before = service.inspect("world-zero");
            repository.fail = true;
            assertThrows(IOException.class, () -> service.supply("world-zero", "alice", ID, 3));
            assertEquals(before, service.inspect("world-zero"));
            assertTrue(published.isEmpty());
            repository.fail = false;
            assertFalse(service.supply("world-zero", "alice", ID, 3).duplicate());
            assertEquals(1, published.size());
            assertTrue(service.supply("world-zero", "alice", ID, 3).duplicate());
            assertEquals(1, published.size());
        }
    }
    @Test void publicationFailureCannotRollBackAcknowledgedDurableState() throws IOException {
        Path file = temp.resolve("publish.simulation");
        try (var service = open(new FileSimulationRepository(file), e -> { throw new IllegalStateException("transport down"); })) {
            assertTrue(service.supply("world-zero", "alice", ID, 3).state().questCompleted());
        }
        try (var service = open(new FileSimulationRepository(file), e -> { })) {
            assertTrue(service.supply("world-zero", "alice", ID, 3).duplicate());
        }
    }
    @Test void lostSaveAcknowledgmentIsReconciledBeforeRetry() throws IOException {
        var repository = new MemoryRepository();
        try (var service = open(repository, e -> { })) {
            repository.loseAcknowledgment = true;
            assertThrows(IOException.class, () -> service.supply("world-zero", "alice", ID, 3));
            repository.loseAcknowledgment = false;
            assertTrue(service.supply("world-zero", "alice", ID, 3).duplicate());
            assertEquals(0, service.inspect("world-zero").cisternWater());
        }
    }
    @Test void unresolvableSaveOutcomeStopsFurtherReadsAndWrites() throws IOException {
        var repository = new MemoryRepository();
        try (var service = open(repository, e -> { })) {
            repository.fail = true;
            repository.failRead = true;
            assertThrows(IOException.class, () -> service.supply("world-zero", "alice", ID, 3));
            assertThrows(IllegalStateException.class, () -> service.inspect("world-zero"));
            assertThrows(IllegalStateException.class, () -> service.supply("world-zero", "alice", ID, 3));
            assertThrows(IllegalStateException.class, service::advance);
        }
    }
    @Test void concurrentRetriesHaveOneReceiptAndOneTransfer() throws Exception {
        try (var service = open(new FileSimulationRepository(temp.resolve("race.simulation")), e -> { });
             var executor = Executors.newFixedThreadPool(4)) {
            var jobs = new ArrayList<java.util.concurrent.Future<LivingWorldService.ActionResult>>();
            for (int i = 0; i < 20; i++) jobs.add(executor.submit(() -> service.supply("world-zero", "alice", ID, 3)));
            int fresh = 0;
            for (var job : jobs) if (!job.get(10, TimeUnit.SECONDS).duplicate()) fresh++;
            assertEquals(1, fresh);
            assertEquals(0, service.inspect("world-zero").cisternWater());
            assertEquals(3, service.inspect("world-zero").keeperWater());
        }
    }
    @Test void ownershipAndMalformedActionsNeverMutateEvenInDevProfile() throws IOException {
        try (var service = open(new FileSimulationRepository(temp.resolve("auth.simulation")), e -> { })) {
            var before = service.inspect("world-zero");
            assertThrows(SecurityException.class, () -> service.supply("world-zero", "bob", ID, 3));
            assertThrows(SecurityException.class, () -> service.supply("world-zero", null, ID, 3));
            assertThrows(IllegalArgumentException.class, () -> service.supply("world-zero", "alice", "bad-id", 3));
            assertThrows(IllegalArgumentException.class, () -> service.inspect("missing-world"));
            assertEquals(before, service.inspect("world-zero"));
        }
    }
    @Test void fileWriterLeaseAndCorruptionFailClosed() throws IOException {
        Path file = temp.resolve("lease.simulation");
        assertThrows(IOException.class, () -> new FileSimulationRepository(temp.toAbsolutePath().getRoot()));
        try (var service = open(new FileSimulationRepository(file), e -> { })) {
            assertThrows(IOException.class, () -> new FileSimulationRepository(file));
            assertEquals(0, service.inspect("world-zero").tick());
        }
        byte[] bytes = Files.readAllBytes(file); bytes[20] ^= 1; Files.write(file, bytes);
        assertThrows(IOException.class, () -> open(new FileSimulationRepository(file), e -> { }));
        try (var repository = new FileSimulationRepository(file)) {
            assertThrows(IOException.class, repository::load);
        }
    }
    @Test void inactiveCatchupIsBoundedClockReversalDoesNotRewindAndConfigCannotSilentlyReset() throws IOException {
        Path file = temp.resolve("time.simulation");
        try (var service = open(new FileSimulationRepository(file), e -> { })) {
            clock[0] = 1_001_000;
            service.advance();
            var first = service.inspect("world-zero");
            assertEquals(64, first.tick());
            assertFalse(first.active());
            clock[0] = 999;
            service.advance();
            assertEquals(first, service.inspect("world-zero"));
        }
        assertThrows(IOException.class, () -> new LivingWorldService(new FileSimulationRepository(file), WorldId.ZERO,
                1, "alice", 1000, () -> clock[0], e -> { }, new SimpleMeterRegistry()));
    }
    @Test void existingHttpTransportProvidesUnrealConsumableVersionedSnapshotsAndEvents() throws Exception {
        var stomp = mock(SimpMessagingTemplate.class);
        List<LivingWorldService.Update> events = new ArrayList<>();
        try (var service = open(new FileSimulationRepository(temp.resolve("http.simulation")), events::add)) {
            var controller = new LivingWorldController(service, stomp);
            var mvc = MockMvcBuilders.standaloneSetup(controller).setControllerAdvice(new ApiExceptionHandler()).build();
            String url = "/api/v1/world/world-zero/simulation/v1";
            mvc.perform(get(url).header("User-Agent", "DaedalusLink-contract-test"))
                    .andExpect(status().isOk()).andExpect(jsonPath("$.schemaVersion").value(1))
                    .andExpect(jsonPath("$.cisternWater").value(3));
            String body = "{\"requestId\":\"" + ID + "\",\"water\":3}";
            mvc.perform(post(url + "/actions/supply").contentType("application/json").content(body))
                    .andExpect(status().isUnauthorized());
            mvc.perform(post(url + "/actions/supply").principal(() -> "bob").contentType("application/json").content(body))
                    .andExpect(status().isForbidden());
            mvc.perform(post(url + "/actions/supply").principal(() -> "alice").contentType("application/json").content(body))
                    .andExpect(status().isOk()).andExpect(jsonPath("$.duplicate").value(false))
                    .andExpect(jsonPath("$.state.questCompleted").value(true));
            mvc.perform(post(url + "/actions/supply").principal(() -> "alice").contentType("application/json").content(body))
                    .andExpect(status().isOk()).andExpect(jsonPath("$.duplicate").value(true));
            mvc.perform(get(url)).andExpect(jsonPath("$.rememberedActor").value("alice"))
                    .andExpect(jsonPath("$.cisternWater").value(0));
            controller.updated(events.getFirst());
            verify(stomp).convertAndSend(eq("/topic/world/world-zero/simulation/v1"), any(LivingWorldService.Update.class));
            mvc.perform(post(url + "/actions/supply").principal(() -> "alice").contentType("application/json")
                    .content("{\"requestId\":\"bad\",\"water\":-1}"))
                    .andExpect(status().isBadRequest());
        }
    }
    @Test void completeJvmTerminationAndRestartRetainCommittedReceipt() throws Exception {
        Path file = temp.resolve("process.simulation");
        for (String mode : List.of("write", "read")) {
            Path log = temp.resolve(mode + ".log");
            String java = Path.of(System.getProperty("java.home"), "bin", "java").toString();
            Process process = new ProcessBuilder(java, "-Xmx128m", "-cp",
                    System.getProperty("surefire.test.class.path", System.getProperty("java.class.path")),
                    LivingWorldRestartProbe.class.getName(), mode, file.toString())
                    .redirectErrorStream(true).redirectOutput(log.toFile()).start();
            if (!process.waitFor(20, TimeUnit.SECONDS)) {
                process.destroyForcibly(); fail("Restart child timed out");
            }
            assertEquals(0, process.exitValue(), Files.readString(log));
            assertTrue(Files.readString(log).contains("RECOVERY_OK"), Files.readString(log));
        }
    }
    private static final class MemoryRepository implements SimulationRepository {
        private SimulationCodec.Stored value;
        private boolean fail;
        private boolean loseAcknowledgment;
        private boolean failRead;
        @Override public SimulationCodec.Stored load() throws IOException {
            if (failRead) throw new IOException("Storage cannot be read");
            return value;
        }
        @Override public void save(SimulationCodec.Stored state) throws IOException {
            if (fail) throw new IOException("Injected storage failure");
            value = state;
            if (loseAcknowledgment) throw new IOException("Lost acknowledgment after commit");
        }
        @Override public void close() { }
    }
}
