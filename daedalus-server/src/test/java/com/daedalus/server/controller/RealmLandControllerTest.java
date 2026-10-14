// SPDX-License-Identifier: MIT
package com.daedalus.server.controller;

import com.daedalus.server.service.RealmLandService;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

class RealmLandControllerTest {
    @Test void refusesMissingOrBlankIdentityBeforeReadingDisk() {
        var service = mock(RealmLandService.class);
        var controller = new RealmLandController(service);
        for (java.security.Principal principal : new java.security.Principal[]{null, () -> null, () -> " "}) {
            assertThatExceptionOfType(ResponseStatusException.class)
                    .isThrownBy(() -> controller.district("OCEAN", 55, principal))
                    .satisfies(ex -> assertThat(ex.getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED));
        }
        verifyNoInteractions(service);
    }
}
