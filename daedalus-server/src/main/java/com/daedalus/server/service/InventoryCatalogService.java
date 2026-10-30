package com.daedalus.server.service;

import com.daedalus.world.inventory.InventoryCatalog;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import org.springframework.stereotype.Service;

/** Read-only catalogs shared with Unreal; does not expose a player's bag. */
@Service
public class InventoryCatalogService {
    private final Map<String, InventoryCatalog> catalogs;

    public InventoryCatalogService() {
        Map<String, InventoryCatalog> loaded = new LinkedHashMap<>();
        for (String key : new String[]{"world-zero", "gallery-city", "parcels", "bricks", "labyrinth", "ocean"}) {
            try (var stream = InventoryCatalog.class.getResourceAsStream("/inventory/" + key + ".dic")) {
                if (stream == null) throw new IllegalStateException("Missing inventory catalog: " + key);
                var catalog = InventoryCatalog.parse(new String(stream.readAllBytes(), StandardCharsets.UTF_8));
                if (!catalog.realm().equals(key.toUpperCase(Locale.ROOT))) {
                    throw new IllegalStateException("Inventory realm mismatch: " + key);
                }
                loaded.put(key, catalog);
            } catch (IOException e) {
                throw new IllegalStateException("Cannot read inventory catalog: " + key, e);
            }
        }
        catalogs = Map.copyOf(loaded);
    }

    public InventoryCatalog find(String realm) { return catalogs.get(realm); }
}
