// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox.radio;

import java.net.URI;

/** Vets a URL before the radio relay fetches it ({@link RelayGuard} in production). Throws {@link RelayGuard.Refused}. */
@FunctionalInterface
public interface UrlCheck {
    URI check(String url);
}
