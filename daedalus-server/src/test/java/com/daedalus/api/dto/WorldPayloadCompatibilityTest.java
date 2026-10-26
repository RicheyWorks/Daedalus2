// SPDX-License-Identifier: MIT
package com.daedalus.api.dto;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import java.lang.reflect.Constructor;
import java.lang.reflect.Parameter;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.stream.Stream;
import static org.assertj.core.api.Assertions.*;

/** Pins the historical constructor families and their additive JSON defaults for world clients. */
class WorldPayloadCompatibilityTest {
    private final ObjectMapper json = new ObjectMapper();
    private static final Set<String> OPTIONAL = Set.of("street", "lot", "maze", "lease", "place", "occupants", "stands",
            "acl", "drive", "driveActor", "driveAt", "box", "boxes", "leases", "mazes", "lots", "acls", "places",
            "occupant", "actor", "at");

    static Stream<Arguments> contracts() {
        return Stream.of(
                Arguments.of(WorldInspectResponse.class, new int[]{10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21}),
                Arguments.of(ChunkInspectResponse.class, new int[]{6, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24}),
                Arguments.of(BlockInspectResponse.class, new int[]{10, 11, 13, 14}),
                Arguments.of(BlockMutationResponse.class, new int[]{6, 7, 8, 9, 10, 11, 12}),
                Arguments.of(DoorInspectResponse.class, new int[]{6, 8, 9, 11, 12, 13, 14}),
                Arguments.of(NpcInspectResponse.class, new int[]{6, 8, 9, 11, 12, 13, 14}),
                Arguments.of(PortalInspectResponse.class, new int[]{6, 8, 9, 11, 12, 13, 14}),
                Arguments.of(TrapInspectResponse.class, new int[]{6, 8, 9, 11, 12, 13, 14}),
                Arguments.of(DoorMutationResponse.class, new int[]{4, 5, 6, 7, 8, 9}),
                Arguments.of(NpcMutationResponse.class, new int[]{4, 5, 6, 7, 8, 9}),
                Arguments.of(PortalMutationResponse.class, new int[]{4, 5, 6, 7, 8, 9}),
                Arguments.of(TrapMutationResponse.class, new int[]{4, 5, 6, 7, 8, 9}),
                Arguments.of(ParcelDenyResponse.class, new int[]{3, 4, 5, 6, 7}),
                Arguments.of(ParcelForgiveResponse.class, new int[]{3, 4, 5, 6, 7}),
                Arguments.of(ParcelGrantResponse.class, new int[]{3, 4, 5, 6, 7}),
                Arguments.of(ParcelRevokeResponse.class, new int[]{3, 4, 5, 6, 7}),
                Arguments.of(ParcelLeaseResponse.class, new int[]{3, 4, 5, 6}),
                Arguments.of(ParcelReleaseResponse.class, new int[]{3, 4, 5, 6}),
                Arguments.of(StampMutationResponse.class, new int[]{8, 9, 10, 11}),
                Arguments.of(WorldEventFrame.class, new int[]{8, 10, 11, 14, 15, 16, 17}),
                Arguments.of(WorldObserveResponse.class, new int[]{10, 11, 13, 14, 15}),
                Arguments.of(WorldTraceStepResponse.class, new int[]{3, 4, 5, 6, 7, 8, 9, 10}),
                Arguments.of(WorldParcelRow.class, new int[]{8, 9}));
    }

    @ParameterizedTest(name = "{0}: old signatures and JSON round trip")
    @MethodSource("contracts")
    void historicalSignaturesPreserveFieldsAndDefaultOnlyNewFields(Class<?> type, int[] legacyArities) throws Exception {
        assertThat(Arrays.stream(type.getConstructors()).mapToInt(Constructor::getParameterCount).toArray()).contains(legacyArities);
        for (var constructor : type.getConstructors()) {
            var supplied = new HashMap<String, Object>();
            Object[] arguments = Arrays.stream(constructor.getParameters()).map(p -> {
                assertThat(p.isNamePresent()).as("compiler must preserve public constructor parameter names").isTrue();
                Object value = sample(p);
                supplied.put(p.getName(), value);
                return value;
            }).toArray();
            Object payload = constructor.newInstance(arguments);
            assertThat(Arrays.stream(type.getRecordComponents()).map(c -> c.getName()).toList()).containsAll(supplied.keySet());
            var tree = json.valueToTree(payload);
            assertThat(tree.size()).isEqualTo(type.getRecordComponents().length);
            for (var component : type.getRecordComponents()) {
                Object expected = supplied.containsKey(component.getName()) ? supplied.get(component.getName())
                        : absentValue(type, component.getName(), component.getType());
                assertThat(component.getAccessor().invoke(payload)).as("%s: %s", constructor, component.getName()).isEqualTo(expected);
                assertThat(tree.get(component.getName())).isEqualTo(json.valueToTree(expected));
            }
            assertThat(json.readValue(json.writeValueAsBytes(payload), type)).isEqualTo(payload);
        }
    }

    @ParameterizedTest(name = "{0}: omitted optional JSON fields")
    @MethodSource("contracts")
    void olderJsonMayOmitNewOptionalFields(Class<?> type, int[] ignoredArities) throws Exception {
        var canonical = Arrays.stream(type.getConstructors()).filter(c -> c.getParameterCount() == type.getRecordComponents().length)
                .findFirst().orElseThrow();
        Map<String, Object> request = new HashMap<>();
        for (Parameter p : canonical.getParameters()) if (!OPTIONAL.contains(p.getName())) request.put(p.getName(), sample(p));
        Object payload = json.readValue(json.writeValueAsBytes(request), type);
        var tree = json.valueToTree(payload);
        for (var component : type.getRecordComponents()) {
            if (OPTIONAL.contains(component.getName())) assertThat(tree.get(component.getName()).asText()).isEmpty();
        }
        if (type == WorldInspectResponse.class || type == ChunkInspectResponse.class) {
            request.put("plots", -1);
            assertThatThrownBy(() -> json.readValue(json.writeValueAsBytes(request), type)).hasRootCauseInstanceOf(IllegalArgumentException.class);
        }
    }

    private static Object absentValue(Class<?> type, String name, Class<?> fieldType) {
        if (type == BlockMutationResponse.class && name.equals("result")) return "PLACED";
        if (fieldType == int.class) return 0;
        if (fieldType == String.class) return "";
        throw new AssertionError("Define a compatibility default for " + type + "." + name);
    }
    private static Object sample(Parameter p) {
        if (p.getType() == String.class) return "fixture-" + p.getName() + "-α";
        if (p.getType() == int.class) return switch (p.getName()) { case "x", "minX" -> 3; case "y" -> 5; default -> 7; };
        if (p.getType() == long.class || p.getType() == Long.class) return 9_007_199_254_740_991L;
        if (p.getType() == boolean.class) return true;
        throw new AssertionError("Define a fixture for " + p);
    }
}
