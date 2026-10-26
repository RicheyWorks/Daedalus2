// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.world.island.VoxelIsle;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.Base64;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.equalTo;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class ReachControllerTest {

    private final MockMvc mvc = MockMvcBuilders.standaloneSetup(new ReachController()).build();

    @Test
    void servesTheFiveIslesWithTheirSettings() throws Exception {
        mvc.perform(get("/api/v1/reach/orrery"))
                .andExpect(status().isOk())
                .andExpect(header().string("Cache-Control", "max-age=3600"))
                .andExpect(jsonPath("$.isles.length()", equalTo(5)))
                .andExpect(jsonPath("$.isles[0].name", equalTo("Claude Island")))
                .andExpect(jsonPath("$.isles[0].radius", equalTo(140)))
                .andExpect(jsonPath("$.isles[0].grid", equalTo(285)))
                .andExpect(jsonPath("$.bridges.length()", equalTo(3)));
    }

    @Test
    @SuppressWarnings("unchecked")
    void theColumnsDecodeToTheGeneratorsOwnHeights() {
        Map<String, Object> body = ReachController.build();
        List<Map<String, Object>> isles = (List<Map<String, Object>>) body.get("isles");
        for (int i = 0; i < isles.size(); i++) {
            Map<String, Object> isle = isles.get(i);
            VoxelIsle.Params p = VoxelIsle.orreryReach().get(i).params();
            int n = p.radius() + 2;
            int w = (int) isle.get("grid");
            ByteBuffer tops = ByteBuffer.wrap(Base64.getDecoder().decode((String) isle.get("tops")))
                    .order(ByteOrder.LITTLE_ENDIAN);
            ByteBuffer bots = ByteBuffer.wrap(Base64.getDecoder().decode((String) isle.get("bottoms")))
                    .order(ByteOrder.LITTLE_ENDIAN);
            assertThat(tops.capacity()).isEqualTo(w * w * 2);
            for (int y = -n; y <= n; y += 7) {
                for (int x = -n; x <= n; x += 5) {
                    int at = ((y + n) * w + (x + n)) * 2;
                    int top = VoxelIsle.columnTop(p, x, y);
                    short got = tops.getShort(at);
                    assertThat(got == Short.MIN_VALUE ? VoxelIsle.OFF : got).as("%s %d,%d", isle.get("name"), x, y)
                            .isEqualTo(top);
                    if (top != VoxelIsle.OFF) {
                        assertThat((int) bots.getShort(at)).isEqualTo(VoxelIsle.columnBottom(p, x, y));
                    }
                }
            }
        }
    }
}
