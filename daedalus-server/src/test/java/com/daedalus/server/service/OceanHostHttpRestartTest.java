// SPDX-License-Identifier: MIT
package com.daedalus.server.service;

import com.daedalus.server.DaedalusApp;
import com.daedalus.server.security.JwtTokenService;
import com.daedalus.world.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.*;
import java.nio.file.Path;
import java.nio.file.Files;
import java.time.Duration;
import java.util.Base64;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.web.server.context.WebServerApplicationContext;
import org.springframework.context.ConfigurableApplicationContext;
import static org.assertj.core.api.Assertions.*;

/** Real loopback HTTP, production JWT filter and full application restart. */
class OceanHostHttpRestartTest {
    @TempDir Path tmp;
    private final ObjectMapper json=new ObjectMapper();
    @Test void productionHttpRequiresJwtAndReturnsPersistentCompatibleChunksAfterRestart() throws Exception {
        try(var client=HttpClient.newHttpClient()) {
            try(var app=start()) {
                URI base=base(app);String token=app.getBean(JwtTokenService.class).issue("alice").token();
                URI directoryUri=base.resolve("/api/v1/realms");
                assertThat(get(client,directoryUri,null).statusCode()).isEqualTo(401);
                String directoryToken=app.getBean(JwtTokenService.class).issue("directory-client").token();
                var directoryResponse=get(client,directoryUri,directoryToken);
                assertThat(directoryResponse.statusCode()).isEqualTo(200);
                var directory=json.readTree(directoryResponse.body());
                assertThat(directory.path("schemaVersion").asInt()).isEqualTo(1);
                assertThat(directory.path("realms")).hasSize(2);
                var oceanEntry=directory.path("realms").get(1);
                assertThat(oceanEntry.path("id").asText()).isEqualTo("ocean");
                assertThat(oceanEntry.path("protocol").asText()).isEqualTo("OCEAN_V1");
                assertThat(oceanEntry.path("blockEditsSupported").asBoolean()).isFalse();
                String chunkPath=oceanEntry.path("chunkPathTemplate").asText()
                        .replace("{x}","0").replace("{y}","-1").replace("{z}","0");
                var discoveredChunk=get(client,base.resolve(chunkPath),directoryToken);
                assertThat(discoveredChunk.statusCode()).isEqualTo(200);
                assertThat(Base64.getDecoder().decode(json.readTree(discoveredChunk.body()).path("data").asText())).hasSize(4096);
                assertThat(get(client,base,null).statusCode()).isEqualTo(401);
                assertThat(get(client,URI.create(base+"/chunk?x=0&y=-1&z=0"),"invalid").statusCode()).isEqualTo(401);
                var manifest=get(client,base,token);assertThat(manifest.statusCode()).isEqualTo(200);
                assertThat(json.readTree(manifest.body()).path("realm").asText()).isEqualTo("ocean");
                String bob=app.getBean(JwtTokenService.class).issue("bob").token();
                assertThat(get(client,URI.create(base+"/chunk?x=99&y=0&z=0"),bob).statusCode()).isEqualTo(404);
                app.getBean(OceanHostService.class).set(new BlockCoordinate(1,-1,1),BlockType.GLASS);
                var chunk=get(client,URI.create(base+"/chunk?x=0&y=-1&z=0"),token);
                assertGlass(chunk);
                assertThat(get(client,base,token).statusCode()).isEqualTo(429);
            }
            try(var app=start()) {
                String token=app.getBean(JwtTokenService.class).issue("alice").token();
                assertGlass(get(client,URI.create(base(app)+"/chunk?x=0&y=-1&z=0"),token));
                Files.writeString(tmp.resolve("ocean/1_-1_0.daew"),"corrupt");
                var unavailable=get(client,URI.create(base(app)+"/chunk?x=1&y=-1&z=0"),token);
                assertThat(unavailable.statusCode()).isEqualTo(503);
                assertThat(unavailable.body()).doesNotContain(tmp.toString());
            }
        }
    }
    private void assertGlass(HttpResponse<String> response) throws Exception {
        assertThat(response.statusCode()).isEqualTo(200);
        var dto=json.readTree(response.body());byte[] blocks=Base64.getDecoder().decode(dto.path("data").asText());
        assertThat(blocks).hasSize(4096);
        assertThat(dto.path("palette").get(Byte.toUnsignedInt(blocks[1+16*(15+16)])).asText()).isEqualTo("GLASS");
    }
    private ConfigurableApplicationContext start() {
        return new SpringApplicationBuilder(DaedalusApp.class).profiles("prod","test").run(
                "--server.port=0","--server.address=127.0.0.1","--daedalus.redis.enabled=false",
                "--daedalus.security.jwt.secret=ocean-http-restart-test-only-secret-123456!",
                "--daedalus.security.admin.password-bcrypt=$2a$10$7EqJtq98hPqEX7fNZaFWoOhi5B0h6C1JcqIcnLmVjKobXAB9Zwmqu",
                "--daedalus.plugins.directory="+tmp.resolve("plugins"),"--daedalus.plugins.scan-on-startup=false",
                "--daedalus.world.file="+tmp.resolve("world.daew"),"--daedalus.ocean.enabled=true",
                "--daedalus.ocean.directory="+tmp.resolve("ocean"),"--daedalus.ocean.seed=42",
                "--resilience4j.ratelimiter.instances.oceanChunks.limit-for-period=2",
                "--resilience4j.ratelimiter.instances.oceanChunks.limit-refresh-period=1h");
    }
    private URI base(ConfigurableApplicationContext app) {
        int port=((WebServerApplicationContext)app).getWebServer().getPort();return URI.create("http://127.0.0.1:"+port+"/api/v1/ocean/v1");
    }
    private HttpResponse<String> get(HttpClient client,URI uri,String token) throws Exception {
        var request=HttpRequest.newBuilder(uri).timeout(Duration.ofSeconds(10));
        if(token!=null)request.header("Authorization","Bearer "+token);
        return client.send(request.build(),HttpResponse.BodyHandlers.ofString());
    }
}
