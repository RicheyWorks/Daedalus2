// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import io.swagger.v3.oas.models.ExternalDocumentation;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import io.swagger.v3.oas.models.tags.Tag;
import io.swagger.v3.oas.models.servers.Server;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;

/**
 * OpenAPI / Swagger UI metadata for the Daedalus REST surface.
 *
 * <p>Exposed by the {@code springdoc-openapi-starter-webmvc-ui} dependency at:
 * <ul>
 *   <li>{@code /v3/api-docs}        — JSON spec</li>
 *   <li>{@code /v3/api-docs.yaml}   — YAML spec</li>
 *   <li>{@code /swagger-ui.html}    — interactive UI</li>
 * </ul>
 *
 * <p>The bean below sets the document-level info (title, description, version, contact,
 * license placeholder), declares the active server URL, and pre-registers the three controller
 * tags so they show up in a stable order. Per-endpoint summaries live on the controllers
 * themselves via {@code @Operation(summary = "...")}.
 */
@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI daedalusOpenAPI(@Value("${spring.application.name:daedalus-server}") String appName,
                                   @Value("${server.port:8080}") String port) {
        return new OpenAPI()
                .info(new Info()
                        .title("Daedalus API")
                        .description("REST + WebSocket interface to the Daedalus maze / graph engine. "
                                + "All endpoints are mounted under /api/v1. STOMP topics are documented "
                                + "in the project README; they do not appear in this OpenAPI spec because "
                                + "OpenAPI 3.0 does not model STOMP.")
                        .version("1.0.0")
                        .contact(new Contact()
                                .name("Daedalus")
                                .url("https://github.com/")) // TODO: fill in once the repo is public
                        .license(new License()
                                .name("MIT")
                                .url("./LICENSE")))
                .externalDocs(new ExternalDocumentation()
                        .description("Project README + audit + changelog")
                        .url("./README.md"))
                .servers(List.of(
                        new Server().url("http://localhost:" + port).description("Local dev"),
                        new Server().url("/").description("Same-origin (deployed)")))
                .tags(List.of(
                        new Tag().name("Mazes")
                                .description("Generate, fetch, solve, and play mazes."),
                        new Tag().name("Plugins")
                                .description("Inspect plugins discovered and loaded by the runtime."),
                        new Tag().name("Leaderboard")
                                .description("Top-N completion times across active sessions.")));
    }
}
