// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox.radio;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;

/**
 * The free Radio Browser directory (no key). Port of ComputerPets' {@code fetchRadioJson}
 * (desktop/main.cjs): try each mirror in turn with an identifying User-Agent, first good JSON wins.
 */
public final class RadioBrowserDirectory implements RadioDirectory {

    /** ComputerPets' RADIO_HOSTS. */
    public static final List<String> HOSTS = List.of(
            "https://de1.api.radio-browser.info", "https://de2.api.radio-browser.info", "https://fi1.api.radio-browser.info");
    static final String USER_AGENT = "Daedalus-rd-jukebox/1.0 (https://github.com/RicheyWorks/Daedalus2)";

    private static final ObjectMapper JSON = new ObjectMapper();
    private final List<String> hosts;
    private final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(4))
            .followRedirects(HttpClient.Redirect.NORMAL).build();

    public RadioBrowserDirectory(List<String> hosts) {
        this.hosts = hosts == null || hosts.isEmpty() ? HOSTS : List.copyOf(hosts);
    }

    @Override
    public List<RadioStation> search(String pathAndQuery) {
        Exception last = null;
        for (String host : hosts) {
            try {
                HttpRequest req = HttpRequest.newBuilder(URI.create(host + pathAndQuery)).timeout(Duration.ofSeconds(8))
                        .header("User-Agent", USER_AGENT).header("Accept", "application/json").GET().build();
                HttpResponse<String> res = http.send(req, HttpResponse.BodyHandlers.ofString());
                if (res.statusCode() != 200) {
                    last = new IllegalStateException("radio " + res.statusCode());
                    continue;
                }
                return RadioStation.parse(JSON.readTree(res.body()));
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new IllegalStateException("interrupted", e);
            } catch (Exception e) {
                last = e;
            }
        }
        throw new IllegalStateException("can't reach the radio directory", last);
    }
}
