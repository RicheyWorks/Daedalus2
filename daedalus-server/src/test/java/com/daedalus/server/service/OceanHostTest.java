// SPDX-License-Identifier: MIT
package com.daedalus.server.service;

import com.daedalus.server.config.OceanHostConfiguration;
import com.daedalus.server.controller.OceanHostController;
import com.daedalus.world.*;
import java.nio.file.*;
import java.util.Base64;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.web.server.ResponseStatusException;
import static org.assertj.core.api.Assertions.*;

class OceanHostTest {
    @TempDir Path tmp;
    @Test void configurationIsDisabledByDefault() {
        new ApplicationContextRunner().withUserConfiguration(OceanHostConfiguration.class)
                .run(context->assertThat(context).doesNotHaveBean(OceanHostService.class));
    }
    @Test void boundsRejectOversizedAndOverflowingSectors() {
        assertThatThrownBy(()->new OceanHostService.Bounds(1,0,0,0,0,0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(()->new OceanHostService.Bounds(0,4096,0,0,0,0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(()->new OceanHostService.Bounds(0,16,0,16,0,16)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(()->new OceanHostService.Bounds(Integer.MIN_VALUE,Integer.MAX_VALUE,0,0,0,0)).isInstanceOf(IllegalArgumentException.class);
    }
    @Test void readDtoMatchesExistingPaletteAndUnauthenticatedRequestsCannotGenerate() throws Exception {
        Path root=tmp.resolve("sea");
        try(var host=new OceanHostService(root,42,2,new OceanHostService.Bounds(-2,1,-3,0,-2,1))) {
            var controller=new OceanHostController(host);
            assertThatThrownBy(()->controller.chunk(0,-1,0,null)).isInstanceOf(ResponseStatusException.class);
            assertThat(Files.exists(root.resolve("0_-1_0.daew"))).isFalse();
            var dto=controller.chunk(0,-1,0,()->"alice");
            assertThat(dto.present()).isTrue();
            byte[] blocks=Base64.getDecoder().decode(dto.data());
            assertThat(blocks).hasSize(4096);
            assertThat(dto.palette().get(Byte.toUnsignedInt(blocks[0]))).isEqualTo("WATER");
            assertThatThrownBy(()->controller.chunk(99,0,0,()->"alice")).isInstanceOf(ResponseStatusException.class);
            assertThat(Files.exists(root.resolve("99_0_0.daew"))).isFalse();
        }
    }
}
