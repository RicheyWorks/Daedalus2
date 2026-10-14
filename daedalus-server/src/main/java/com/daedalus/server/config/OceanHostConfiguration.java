// SPDX-License-Identifier: MIT
package com.daedalus.server.config;

import com.daedalus.server.service.OceanHostService;
import java.io.IOException;
import java.nio.file.Path;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@ConditionalOnProperty(name="daedalus.ocean.enabled",havingValue="true")
public class OceanHostConfiguration {
    @Bean(destroyMethod="close")
    public OceanHostService oceanHostService(
            @Value("${daedalus.ocean.directory}") Path directory,
            @Value("${daedalus.ocean.seed}") long seed,
            @Value("${daedalus.ocean.capacity:128}") int capacity,
            @Value("${daedalus.ocean.min-x:-2}") int minX,@Value("${daedalus.ocean.max-x:1}") int maxX,
            @Value("${daedalus.ocean.min-y:-3}") int minY,@Value("${daedalus.ocean.max-y:0}") int maxY,
            @Value("${daedalus.ocean.min-z:-2}") int minZ,@Value("${daedalus.ocean.max-z:1}") int maxZ) throws IOException {
        return new OceanHostService(directory,seed,capacity,new OceanHostService.Bounds(minX,maxX,minY,maxY,minZ,maxZ));
    }
}
