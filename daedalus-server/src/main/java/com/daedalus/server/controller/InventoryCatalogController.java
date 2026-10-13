package com.daedalus.server.controller;

import com.daedalus.server.service.InventoryCatalogService;
import com.daedalus.world.inventory.InventoryCatalog;
import com.daedalus.server.web.ResourceNotFoundException;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/inventory")
public class InventoryCatalogController {
    private final InventoryCatalogService catalogs;
    public InventoryCatalogController(InventoryCatalogService catalogs) { this.catalogs = catalogs; }

    @GetMapping("/{realm}/catalog")
    public ResponseEntity<InventoryCatalog> catalog(@PathVariable String realm) {
        var catalog = catalogs.find(realm);
        if (catalog == null) {
            throw new ResourceNotFoundException("inventory catalog", realm, "No inventory catalog for this realm");
        }
        return ResponseEntity.ok(catalog);
    }
}
