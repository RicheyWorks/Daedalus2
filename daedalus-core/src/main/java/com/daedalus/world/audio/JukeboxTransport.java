package com.daedalus.world.audio;

import java.io.IOException;

/** The one seam between the jukebox client and the network; tests and engines plug their own. */
@FunctionalInterface
public interface JukeboxTransport {
    /**
     * Performs a GET.
     *
     * @param url absolute url
     * @return status and body
     * @throws IOException on network failure
     */
    Response get(String url) throws IOException;

    /**
     * HTTP response.
     *
     * @param status status code
     * @param body response body bytes
     */
    record Response(int status, byte[] body) {
        /** Defensive copy. */
        public Response {
            body = body == null ? new byte[0] : body.clone();
        }

        @Override
        public byte[] body() {
            return body.clone();
        }
    }
}
