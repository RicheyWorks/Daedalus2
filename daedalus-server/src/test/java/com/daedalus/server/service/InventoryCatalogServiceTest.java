package com.daedalus.server.service;

import com.daedalus.server.controller.InventoryCatalogController;
import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class InventoryCatalogServiceTest {
    @Test void servesSharedCatalogOverHttpAndRejectsUnknownRealm() throws Exception {
        var mvc = MockMvcBuilders.standaloneSetup(new InventoryCatalogController(new InventoryCatalogService()))
                .setControllerAdvice(new com.daedalus.server.web.ApiExceptionHandler()).build();
        mvc.perform(get("/api/v1/inventory/gallery-city/catalog"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.realm").value("GALLERY-CITY"))
                .andExpect(jsonPath("$.theme").value("gallery"))
                .andExpect(jsonPath("$.items").isArray());
        mvc.perform(get("/api/v1/inventory/missing/catalog")).andExpect(status().isNotFound());
    }
    @Test void loadsEveryCanonicalRealmWithoutSharingOrTransferringCounts() {
        var service = new InventoryCatalogService();
        for (String key : new String[]{"world-zero", "gallery-city", "parcels", "bricks", "labyrinth"}) {
            var catalog = service.find(key);
            assertThat(catalog).isNotNull();
            assertThat(catalog.tabs()).isNotEmpty();
            assertThat(catalog.items()).isNotEmpty();
        }
        assertThat(service.find("gallery-city").items()).isNotEqualTo(service.find("bricks").items());
        assertThat(service.find("../bricks")).isNull();
        var controller = new InventoryCatalogController(service);
        assertThatThrownBy(() -> controller.catalog("missing"))
                .isInstanceOf(com.daedalus.server.web.ResourceNotFoundException.class);
        assertThat(controller.catalog("gallery-city").getStatusCode().value()).isEqualTo(200);
    }
}
