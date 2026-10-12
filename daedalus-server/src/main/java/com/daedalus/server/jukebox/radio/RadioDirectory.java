// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox.radio;

import java.util.List;

/** Fetches one Radio Browser search URL path+query (e.g. "/json/stations/search?…"). Swappable for tests. */
@FunctionalInterface
public interface RadioDirectory {
    List<RadioStation> search(String pathAndQuery);
}
