package com.daedalus.world.audio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class JukeboxClientTest {
    private final List<String> calls = new ArrayList<>();
    private final Deque<Object> script = new ArrayDeque<>();

    private JukeboxTransport fake() {
        return url -> {
            calls.add(url);
            Object o = script.isEmpty() ? 200 : script.poll();
            if (o instanceof IOException e) {
                throw e;
            }
            int st = (Integer) o;
            return new JukeboxTransport.Response(st, ("{\"s\":" + st + "}").getBytes(StandardCharsets.UTF_8));
        };
    }

    @Test
    void buildsStableUrls() throws IOException {
        JukeboxClient c = new JukeboxClient("http://h:8080/", fake(), 0, 3);
        assertEquals("{\"s\":200}", c.config());
        c.arrangement("my song & co");
        c.studioNote(Map.of("voice", "flute", "midi", "60"));
        c.tokenHash(7);
        c.seedFile("a b.wav");
        assertEquals(List.of("http://h:8080/api/v1/jukebox/config",
                "http://h:8080/api/v1/jukebox/arrangement?source=my%20song%20%26%20co",
                "http://h:8080/api/v1/jukebox/studio/note?midi=60&voice=flute",
                "http://h:8080/api/v1/jukebox/tokens/7/hash",
                "http://h:8080/api/v1/jukebox/seeds/a%20b.wav"), calls);
    }

    @Test
    void retriesTransientThenSucceeds() throws IOException {
        JukeboxClient c = new JukeboxClient("http://h", fake(), 2, 3);
        script.add(503);
        script.add(new IOException("reset"));
        script.add(200);
        assertEquals("{\"s\":200}", c.seeds());
        assertEquals(3, calls.size());
    }

    @Test
    void clientErrorsAreNotRetried() {
        JukeboxClient c = new JukeboxClient("http://h", fake(), 3, 5);
        script.add(404);
        JukeboxClient.JukeboxException e = assertThrows(JukeboxClient.JukeboxException.class, () -> c.tokenHash(1));
        assertEquals(404, e.status());
        assertEquals(1, calls.size());
    }

    @Test
    void breakerOpensAndResets() throws IOException {
        JukeboxClient c = new JukeboxClient("http://h", fake(), 0, 2);
        script.add(500);
        script.add(500);
        assertThrows(IOException.class, c::config);
        assertThrows(IOException.class, c::config);
        assertTrue(c.breakerOpen());
        JukeboxClient.JukeboxException e = assertThrows(JukeboxClient.JukeboxException.class, c::config);
        assertEquals(-1, e.status());
        assertEquals(2, calls.size());
        c.reset();
        assertFalse(c.breakerOpen());
        assertEquals("{\"s\":200}", c.config());
    }

    @Test
    void rejectsBadConfig() {
        assertThrows(IllegalArgumentException.class, () -> new JukeboxClient(null, fake(), 0, 1));
        assertThrows(IllegalArgumentException.class, () -> new JukeboxClient("x", fake(), -1, 1));
        assertThrows(IllegalArgumentException.class, () -> new JukeboxClient("x", fake(), 0, 0));
    }
}
