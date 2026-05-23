// SPDX-License-Identifier: MIT

package com.daedalus.server;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * Daedalus — pluggable maze engine.
 *
 * <p>Two boot modes:
 * <ul>
 *   <li>Headless backend (REST + WebSocket + plugin SPI) — run this class directly.</li>
 *   <li>JavaFX desktop client — run {@code com.daedalus.desktop.DaedalusLauncher}, which boots Spring then launches the stage.</li>
 * </ul>
 *
 * <p>{@code scanBasePackages = "com.daedalus"} keeps Spring's component scan rooted at the top
 * of the namespace so beans living outside the {@code com.daedalus.server} subtree
 * (e.g. {@code GeneratorRegistry} in {@code com.daedalus.engine.generators}) are still picked up.
 */
@SpringBootApplication(scanBasePackages = "com.daedalus")
@ConfigurationPropertiesScan("com.daedalus.server.config")
@EnableAsync
public class DaedalusApp {

    private static ConfigurableApplicationContext context;

    public static void main(String[] args) {
        context = SpringApplication.run(DaedalusApp.class, args);
    }

    public static ConfigurableApplicationContext bootHeadless(String[] args) {
        if (context == null) {
            context = new SpringApplicationBuilder(DaedalusApp.class)
                    .headless(true)
                    .web(org.springframework.boot.WebApplicationType.SERVLET)
                    .run(args);
        }
        return context;
    }

    public static ConfigurableApplicationContext context() {
        return context;
    }

    /** Shim so DaedalusLauncher can boot Spring without owning the lifecycle. */
    static final class SpringApplicationBuilder extends org.springframework.boot.builder.SpringApplicationBuilder {
        SpringApplicationBuilder(Class<?>... sources) {
            super(sources);
        }
    }
}
