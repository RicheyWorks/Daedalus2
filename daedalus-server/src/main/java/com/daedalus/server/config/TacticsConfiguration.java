// SPDX-License-Identifier: MIT
package com.daedalus.server.config;

import com.daedalus.server.service.tactics.FileTacticalCheckpoints;
import com.daedalus.world.tactics.AdaptiveDirector;
import com.daedalus.world.tactics.AdaptiveTacticsBrain;
import com.daedalus.world.tactics.TacticalOrders;
import com.daedalus.world.tactics.TacticsHost;
import java.io.IOException;
import java.nio.file.Path;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/** Opt-in single-encounter adaptive host. All strategic context comes from operator configuration. */
@Configuration
public class TacticsConfiguration {
    @Bean(destroyMethod = "close")
    @ConditionalOnProperty(name = "daedalus.tactics.adaptive.enabled", havingValue = "true")
    public FileTacticalCheckpoints tacticalCheckpoints(@Value("${daedalus.tactics.adaptive.directory:}") String directory)
            throws IOException {
        if (directory.isBlank() || directory.contains("${")) throw new IllegalArgumentException("Explicit checkpoint directory required");
        return new FileTacticalCheckpoints(Path.of(directory));
    }

    @Bean
    public TacticsHost tacticsHost(ObjectProvider<FileTacticalCheckpoints> stores,
            @Value("${daedalus.tactics.adaptive.squad:pack-1}") String squad,
            @Value("${daedalus.tactics.adaptive.faction:raiders}") String faction,
            @Value("${daedalus.tactics.adaptive.objective-x:0}") double x,
            @Value("${daedalus.tactics.adaptive.objective-y:0}") double y,
            @Value("${daedalus.tactics.adaptive.objective-z:0}") double z) {
        FileTacticalCheckpoints store = stores.getIfAvailable();
        if (store == null) return new TacticsHost();
        // Validate configured identifiers and coordinates before accepting requests.
        new AdaptiveDirector.Frame(squad, "configuration", 0, java.util.List.of(),
                new TacticalOrders.Vec(x, y, z), new TacticalOrders.Vec(x, y, z), false, AdaptiveDirector.WeaponStyle.UNKNOWN);
        var context = new AdaptiveTacticsBrain.Context(faction, new TacticalOrders.Vec(x, y, z),
                false, AdaptiveDirector.WeaponStyle.UNKNOWN);
        return TacticsHost.withContext(new AdaptiveTacticsBrain(store, roster -> {
            if (!squad.equals(roster.squad())) throw new IllegalArgumentException("Squad not configured for this adaptive host");
            return context;
        }));
    }
}
