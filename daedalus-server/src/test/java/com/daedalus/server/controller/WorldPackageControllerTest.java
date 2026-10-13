// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.server.config.WalletProperties;
import com.daedalus.server.service.WorldHub;
import com.daedalus.server.service.WorldPackageService;
import com.daedalus.server.service.WorldService;
import com.daedalus.server.web.ApiExceptionHandler;
import com.daedalus.world.WorldStyle;
import com.daedalus.world.gate.GateOps;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.beans.factory.support.StaticListableBeanFactory;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.io.ByteArrayInputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * World Packages over HTTP (ADR-032): the zip carries a manifest, a glTF 2.0 world and the ark model; the
 * manifest names islands, gates and arks where the live API puts them; the mesh is rebuilt only when a
 * cube changes, while the manifest always tells the truth about ships; unknown worlds are a 404; a
 * deployed deed contract shows up as the chain block.
 */
class WorldPackageControllerTest {

    @TempDir
    Path tmp;

    private final ObjectMapper json = new ObjectMapper();
    private final long[] clock = {5_000_000L};
    private WorldHub hub;
    private WorldPackageService packages;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        mvc = boot(null);
    }

    private MockMvc boot(WalletProperties wallet) {
        WorldService zero = new WorldService(tmp.resolve("world-zero.daew"), e -> { });
        hub = new WorldHub(zero, e -> { });
        hub.services().forEach(w -> w.useClock(() -> clock[0]));
        zero.raiseIsland("world-zero", 11, 18);
        StaticListableBeanFactory beans = new StaticListableBeanFactory();
        if (wallet != null) {
            beans.addBean("wallet", wallet);
        }
        packages = new WorldPackageService(hub, beans.getBeanProvider(WalletProperties.class));
        return MockMvcBuilders.standaloneSetup(new WorldPackageController(packages))
                .setControllerAdvice(new ApiExceptionHandler()).build();
    }

    private Map<String, byte[]> unzip(byte[] zip) throws Exception {
        Map<String, byte[]> out = new LinkedHashMap<>();
        try (ZipInputStream z = new ZipInputStream(new ByteArrayInputStream(zip))) {
            for (ZipEntry e = z.getNextEntry(); e != null; e = z.getNextEntry()) {
                out.put(e.getName(), z.readAllBytes());
            }
        }
        return out;
    }

    @Test
    void thePackageIsAZipOfManifestGeometryAndTheArk() throws Exception {
        MvcResult r = mvc.perform(get("/api/v1/world/world-zero/package"))
                .andExpect(status().isOk())
                .andExpect(header().string("Content-Type", "application/zip"))
                .andReturn();
        String disposition = r.getResponse().getHeader("Content-Disposition");
        assertThat(disposition).startsWith("attachment; filename=\"world-zero-r").endsWith(".daedalus.zip\"");

        Map<String, byte[]> files = unzip(r.getResponse().getContentAsByteArray());
        assertThat(files).containsKeys("manifest.json", "world.glb", "README.txt");
        if (getClass().getResource("/static/models/ark.glb") != null) {
            assertThat(files).containsKey("assets/ark.glb");
        }
        ByteBuffer glb = ByteBuffer.wrap(files.get("world.glb")).order(ByteOrder.LITTLE_ENDIAN);
        assertThat(glb.getInt(0)).isEqualTo(0x46546C67);
        assertThat(glb.getInt(8)).isEqualTo(files.get("world.glb").length);

        JsonNode m = json.readTree(files.get("manifest.json"));
        assertThat(m.get("format").asText()).isEqualTo(WorldPackageService.FORMAT);
        assertThat(m.get("version").asInt()).isEqualTo(1);
        assertThat(m.get("world").get("id").asText()).isEqualTo("world-zero");
        assertThat(m.get("world").get("style").asText()).isEqualTo("SKY_ISLANDS");
        assertThat(m.get("geometry").get("chunks").asInt()).isPositive();
        assertThat(m.get("geometry").get("triangles").asLong()).isPositive();
        assertThat(m.get("islands")).hasSize(1);
        assertThat(m.get("islands").get(0).get("seed").asLong()).isEqualTo(11);
        assertThat(m.get("arks")).hasSize(1);
        assertThat(m.get("arks").get(0).get("state").asText()).isEqualTo("MOORED");
        assertThat(m.get("mount").get("kind").asText()).isEqualTo("ARK");
        assertThat(m.get("palette").toString()).contains("PORTAL", "RAINBOW_RED");
        assertThat(m.has("chain")).as("no deed contract configured").isFalse();
        assertThat(m.get("generator").asText()).doesNotContain("null");

        // The same world gives the same zip, byte for byte.
        byte[] again = mvc.perform(get("/api/v1/world/world-zero/package")).andReturn().getResponse().getContentAsByteArray();
        assertThat(again).isEqualTo(r.getResponse().getContentAsByteArray());
    }

    @Test
    void theGeometryAndManifestAlsoComeOnTheirOwn() throws Exception {
        MvcResult g = mvc.perform(get("/api/v1/world/world-zero/package/world.glb"))
                .andExpect(status().isOk())
                .andExpect(header().string("Content-Type", "model/gltf-binary"))
                .andReturn();
        assertThat(g.getResponse().getHeader("ETag")).startsWith("\"world-zero-");
        JsonNode m = json.readTree(mvc.perform(get("/api/v1/world/world-zero/package/manifest"))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString());
        assertThat(m.get("geometry").get("file").asText()).isEqualTo("world.glb");
        assertThat(m.get("live").get("api").asText()).endsWith("/api/v1/world/world-zero");
    }

    @Test
    void aGreedyMeshIsSmallerCachedApartAndAskedForByName() throws Exception {
        hub.get("world-zero").raiseIsland("world-zero", 11, com.daedalus.world.island.IslandGenerator.DEFAULT_RADIUS);
        JsonNode faces = json.readTree(mvc.perform(get("/api/v1/world/world-zero/package/manifest"))
                .andReturn().getResponse().getContentAsString());
        JsonNode greedy = json.readTree(mvc.perform(get("/api/v1/world/world-zero/package/manifest").param("mesh", "greedy"))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString());
        long a = faces.get("geometry").get("triangles").asLong();
        long b = greedy.get("geometry").get("triangles").asLong();
        assertThat(b).isPositive().isLessThan(a / 2);
        MvcResult g = mvc.perform(get("/api/v1/world/world-zero/package/world.glb").param("mesh", "greedy"))
                .andExpect(status().isOk()).andReturn();
        assertThat(g.getResponse().getHeader("ETag")).endsWith("-greedy\"");
        byte[] plain = mvc.perform(get("/api/v1/world/world-zero/package/world.glb")).andReturn().getResponse().getContentAsByteArray();
        assertThat(g.getResponse().getContentAsByteArray().length).isLessThan(plain.length);
        mvc.perform(get("/api/v1/world/world-zero/package/world.glb").param("mesh", "cubes")).andExpect(status().isBadRequest());
    }

    @Test
    void anUnknownWorldIsNotFound() throws Exception {
        mvc.perform(get("/api/v1/world/nowhere/package")).andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/world/nowhere/package/manifest")).andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/world/nowhere/package/world.glb")).andExpect(status().isNotFound());
    }

    @Test
    void theMeshIsRebuiltOnlyWhenACubeChangesButShipsAreAlwaysCurrent() throws Exception {
        WorldPackageService.Built a = packages.build("world-zero", "http://x");
        hub.create("isle-two", WorldStyle.SKY_ISLANDS, 42, "Isle Two");
        WorldPackageService.Built b = packages.build("world-zero", "http://x");
        assertThat(packages.meshes()).isEqualTo(1);
        assertThat(b.glb()).isEqualTo(a.glb());
        b.glb()[0] = 0; // a copy: the cached mesh is untouched
        assertThat(packages.build("world-zero", "http://x").glb()[0]).isEqualTo((byte) 'g');

        // A gate is cubes: the revision moves and the mesh grows a rainbow.
        hub.openGate("world-zero", "isle-two");
        WorldPackageService.Built c = packages.build("world-zero", "http://x");
        assertThat(c.revision()).isGreaterThan(a.revision());
        assertThat(packages.meshes()).isEqualTo(2);
        assertThat(c.glb()).isNotEqualTo(a.glb());
        assertThat(c.manifest().geometry().triangles()).isGreaterThan(a.manifest().geometry().triangles());
        assertThat(c.manifest().gates()).hasSize(1);
        assertThat(c.manifest().gates().get(0).toTitle()).isEqualTo("Isle Two");
        assertThat(c.manifest().gates().get(0).slot()).isEqualTo(GateOps.slotOfGate(0));

        // Setting sail moves no cube: same mesh, but the manifest says the ark is under way.
        WorldService zero = hub.get("world-zero");
        assertThat(zero.sail("world-zero", "ark-0", GateOps.slotOfGate(0)).result().name()).isEqualTo("SAILING");
        WorldPackageService.Built d = packages.build("world-zero", "http://x");
        assertThat(packages.meshes()).isEqualTo(2);
        assertThat(d.glb()).isEqualTo(c.glb());
        assertThat(d.manifest().arks().get(0).state()).isEqualTo("SAILING");
    }

    @Test
    void aDeployedDeedContractIsTheChainBlock() throws Exception {
        mvc = boot(new WalletProperties(true, "realm.example", "https://realm.example", 31_337L,
                "0x5FbDB2315678afecb367f032d93F642f64180aa3", "", 30));
        JsonNode m = json.readTree(mvc.perform(get("/api/v1/world/world-zero/package/manifest"))
                .andReturn().getResponse().getContentAsString());
        assertThat(m.get("chain").get("chainId").asLong()).isEqualTo(31_337L);
        assertThat(m.get("chain").get("deedContract").asText()).isEqualTo("0x5FbDB2315678afecb367f032d93F642f64180aa3");
    }
}
