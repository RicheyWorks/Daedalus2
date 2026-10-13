package com.daedalus.server.controller;

import com.daedalus.server.service.InventoryCatalogService;
import com.daedalus.world.inventory.InventoryCatalog;
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
        return catalog == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(catalog);
    }
}
