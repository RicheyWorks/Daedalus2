// SPDX-License-Identifier: MIT
package com.daedalus.server.controller;

import com.daedalus.server.service.RealmDirectoryService;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

class RealmDirectoryControllerTest {
    @Test void missingOrBlankIdentityIsRefusedEvenOutsideTheProductionFilterChain() {
        var service=mock(RealmDirectoryService.class);
        var controller=new RealmDirectoryController(service);
        for (java.security.Principal principal:new java.security.Principal[]{null,()->null,()->" "}) {
            assertThatExceptionOfType(ResponseStatusException.class).isThrownBy(()->controller.realms(principal))
                    .satisfies(error->assertThat(error.getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED));
        }
        verifyNoInteractions(service);
    }
    @Test void conflictingProviderConfigurationHasNoInternalDetailsInThePublicReason() {
        var service=mock(RealmDirectoryService.class);
        when(service.directory()).thenThrow(new IllegalStateException("private storage details"));
        var controller=new RealmDirectoryController(service);
        assertThatExceptionOfType(ResponseStatusException.class).isThrownBy(()->controller.realms(()->"alice"))
                .satisfies(error->{
                    assertThat(error.getStatusCode()).isEqualTo(HttpStatus.SERVICE_UNAVAILABLE);
                    assertThat(error.getReason()).isEqualTo("Realm directory unavailable");
                });
    }
}
