// SPDX-License-Identifier: MIT

package com.daedalus.world.activity;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/** Contract fixtures, validation edges, and canonical round-trip. */
class ActivityResultTest {

    private static final Path CONTRACT = Path.of("..", "docs", "contracts", "activity-result-v1");

    @Test
    void prettyExampleMatchesCanonicalBytesAndTheReceiptHash() throws Exception {
        ActivityResult pretty = ActivityResult.parse(read("prism-pond-caught.json"));
        String canonical = read("prism-pond-caught.canonical.json").strip();
        ActivityResult again = ActivityResult.parse(canonical);

        assertThat(pretty).isEqualTo(again);
        assertThat(pretty.serialize()).isEqualTo(canonical);
        assertThat(ActivityResult.parse(pretty.serialize())).isEqualTo(pretty);
        String hash = HexFormat.of().formatHex(
                MessageDigest.getInstance("SHA-256").digest(canonical.getBytes(StandardCharsets.UTF_8)));
        assertThat(ActivityResultReceipt.idOf(pretty)).isEqualTo(hash);
        assertThat(hash).hasSize(64).matches("[0-9a-f]+");
    }

    @Test
    void missingSubjectIsRefusedAndTheSchemaNamesTheSameVersion() throws IOException {
        assertThatThrownBy(() -> ActivityResult.parse(read("missing-subject.json")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("missing subjectId");
        String schema = read("activity-result.schema.json");
        assertThat(schema).contains("\"const\": \"activity-result/v1\"");
        assertThat(schema).contains("\"subjectId\"");
        assertThat(schema).contains("\"additionalProperties\": false");
    }

    @Test
    void everyOutcomeAndBothKindsRoundTrip() {
        for (ActivityResult.Outcome outcome : ActivityResult.Outcome.values()) {
            ActivityResult result = result(outcome, ActivityResult.SubjectKind.PLANT, Map.of("finish", "done"));
            assertThat(ActivityResult.parse(result.serialize())).isEqualTo(result);
        }
        ActivityResult creature = result(ActivityResult.Outcome.LEARNED, ActivityResult.SubjectKind.CREATURE, Map.of());
        assertThat(creature.serialize()).doesNotContain("detail");
        assertThat(ActivityResult.parse(creature.serialize()).detail()).isEmpty();
    }

    @Test
    void detailIsCopiedSortedAndQuoted() {
        Map<String, String> detail = new HashMap<>();
        detail.put("note", "say \"hi\"\\ok");
        detail.put("finish", "caught");
        ActivityResult result = result(ActivityResult.Outcome.LEARNED, ActivityResult.SubjectKind.CREATURE, detail);
        detail.put("finish", "nope");
        detail.put("extra", "x");

        assertThat(result.detail()).containsExactly(
                Map.entry("finish", "caught"),
                Map.entry("note", "say \"hi\"\\ok"));
        assertThatThrownBy(() -> result.detail().put("z", "z")).isInstanceOf(UnsupportedOperationException.class);
        assertThat(result.serialize()).contains("\\\"hi\\\"\\\\ok");
        assertThat(ActivityResult.parse(result.serialize())).isEqualTo(result);
    }

    @Test
    void unicodeEscapeDecodesBeforeTheTokenRule() {
        ActivityResult result = ActivityResult.parse(field("learned", "\"\\u0072eedling\""));
        assertThat(result.learned()).isEqualTo("reedling");
    }

    @ParameterizedTest
    @ValueSource(strings = {
            "",
            "   ",
            "[]",
            "\"x\"",
            "null",
            "true",
            "1",
            "+1",
            "01",
            "1e309",
            "{",
            "{\"version\":\"activity-result/v1\"}",
            "{\"version\":\"nope\",\"activityId\":\"other.game\",\"attemptId\":\"try-1\",\"subjectId\":\"sunroot\","
                    + "\"subjectKind\":\"PLANT\",\"outcome\":\"LEARNED\",\"learned\":\"reedling\"}"
    })
    void rejectsMalformedOrWrongVersion(String json) {
        assertThatThrownBy(() -> ActivityResult.parse(json)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void rejectsTheDocumentedEdges() {
        assertThatThrownBy(() -> ActivityResult.parse(null)).hasMessageContaining("json is required");
        assertThatThrownBy(() -> ActivityResult.parse("{\"version\":\"" + "v".repeat(5000) + "\"}"))
                .hasMessageContaining("exceeds");
        assertThatThrownBy(() -> ActivityResult.parse("\uFEFF{}")).hasMessageContaining("BOM");
        assertThatThrownBy(() -> ActivityResult.parse(extra("\"score\":1"))).hasMessageContaining("unknown field");
        assertThatThrownBy(() -> ActivityResult.parse(extra("\"version\":\"activity-result/v1\"")))
                .hasMessageContaining("duplicate key");
        assertThatThrownBy(() -> ActivityResult.parse(extra("\"detail\":[]"))).hasMessageContaining("detail must be an object");
        assertThatThrownBy(() -> ActivityResult.parse(extra("\"detail\":{}"))).hasMessageContaining("detail must not be empty");
        assertThatThrownBy(() -> ActivityResult.parse(extra("\"detail\":{\"finish\":1}"))).hasMessageContaining("strings");
        assertThatThrownBy(() -> ActivityResult.parse(extra("\"detail\":null"))).hasMessageContaining("detail must be an object");
        assertThatThrownBy(() -> ActivityResult.parse(field("subjectKind", "\"creature\""))).hasMessageContaining("subjectKind");
        assertThatThrownBy(() -> ActivityResult.parse(field("outcome", "\"WON\""))).hasMessageContaining("outcome");
        assertThatThrownBy(() -> ActivityResult.parse(field("outcome", "1"))).hasMessageContaining("outcome must be a string");
        assertThatThrownBy(() -> ActivityResult.parse(field("version", "1"))).hasMessageContaining("version must be a string");
        assertThatThrownBy(() -> ActivityResult.parse(field("activityId", "\"Prism.pond\""))).hasMessageContaining("bad activityId");
        assertThatThrownBy(() -> ActivityResult.parse(field("activityId", "\"a-\""))).hasMessageContaining("bad activityId");
        assertThatThrownBy(() -> ActivityResult.parse(field("attemptId", "\"cast-\""))).hasMessageContaining("bad attemptId");
        assertThatThrownBy(() -> ActivityResult.parse(field("learned", "\"\""))).hasMessageContaining("bad learned");
        assertThatThrownBy(() -> ActivityResult.parse(field("learned", "\"ripple scattered\""))).hasMessageContaining("bad learned");
        assertThatThrownBy(() -> ActivityResult.parse(field("learned", "\"pati\\nence\""))).hasMessageContaining("bad learned");
        assertThatThrownBy(() -> ActivityResult.parse("{\"version\":\"activity-result/v1\"} trailing"))
                .hasMessageContaining("trailing data");
        assertThatThrownBy(() -> ActivityResult.parse("{\"a\":1,}")).hasMessageContaining("trailing comma");
        assertThatThrownBy(() -> ActivityResult.parse("\"unterminated")).hasMessageContaining("unterminated");
        assertThatThrownBy(() -> ActivityResult.parse("\"bad \\x escape\"")).hasMessageContaining("bad escape");
        assertThatThrownBy(() -> ActivityResult.parse("\"\\u12\"")).hasMessageContaining("unicode");
        assertThatThrownBy(() -> ActivityResult.parse("\"\\uD800\"")).hasMessageContaining("surrogate");
    }

    @Test
    void tokenLengthAndDetailBounds() {
        String fit = "a" + "b".repeat(62) + "c";
        assertThat(fit).hasSize(64);
        ActivityResult ok = ActivityResult.parse(field("activityId", "\"" + fit + "\""));
        assertThat(ok.activityId()).isEqualTo(fit);
        assertThatThrownBy(() -> ActivityResult.parse(field("activityId", "\"" + fit + "d\"")))
                .hasMessageContaining("bad activityId");

        Map<String, String> eight = new HashMap<>();
        for (char c = 'a'; c < 'a' + 8; c++) {
            eight.put(String.valueOf(c), "x");
        }
        assertThat(result(ActivityResult.Outcome.FAILED, ActivityResult.SubjectKind.PLANT, eight).detail()).hasSize(8);
        eight.put("i", "x");
        assertThatThrownBy(() -> result(ActivityResult.Outcome.FAILED, ActivityResult.SubjectKind.PLANT, eight))
                .hasMessageContaining("more than 8");

        Map<String, String> blank = new HashMap<>();
        blank.put("finish", "");
        assertThatThrownBy(() -> result(ActivityResult.Outcome.FAILED, ActivityResult.SubjectKind.PLANT, blank))
                .hasMessageContaining("1..96");
        Map<String, String> huge = Map.of("finish", "x".repeat(97));
        assertThatThrownBy(() -> result(ActivityResult.Outcome.FAILED, ActivityResult.SubjectKind.PLANT, huge))
                .hasMessageContaining("1..96");
        Map<String, String> badKey = Map.of("Finish", "caught");
        assertThatThrownBy(() -> result(ActivityResult.Outcome.FAILED, ActivityResult.SubjectKind.PLANT, badKey))
                .hasMessageContaining("bad detail key");
        Map<String, String> controls = Map.of("finish", "bad\u0001");
        assertThatThrownBy(() -> result(ActivityResult.Outcome.FAILED, ActivityResult.SubjectKind.PLANT, controls))
                .hasMessageContaining("printable ASCII");
        Map<String, String> nil = new HashMap<>();
        nil.put("finish", null);
        assertThatThrownBy(() -> result(ActivityResult.Outcome.FAILED, ActivityResult.SubjectKind.PLANT, nil))
                .hasMessageContaining("detail entries are required");
    }

    @Test
    void constructorRejectsNulls() {
        assertThatThrownBy(() -> new ActivityResult(null, "other.game", "try-1", "sunroot",
                ActivityResult.SubjectKind.PLANT, ActivityResult.Outcome.LEARNED, "reedling", Map.of()))
                .hasMessageContaining("version is required");
        assertThatThrownBy(() -> new ActivityResult(ActivityResult.VERSION, "other.game", "try-1", "sunroot",
                null, ActivityResult.Outcome.LEARNED, "reedling", Map.of()))
                .hasMessageContaining("subjectKind is required");
        assertThatThrownBy(() -> new ActivityResult(ActivityResult.VERSION, "other.game", "try-1", "sunroot",
                ActivityResult.SubjectKind.PLANT, null, "reedling", Map.of()))
                .hasMessageContaining("outcome is required");
    }

    @Test
    void quoteEscapesControls() {
        assertThat(ActivityJson.quote("a\"b\\c")).isEqualTo("\"a\\\"b\\\\c\"");
        assertThat(ActivityJson.quote("\n\r\t\b\f")).isEqualTo("\"\\n\\r\\t\\b\\f\"");
        assertThat(ActivityJson.quote("\u0001")).isEqualTo("\"\\u0001\"");
        assertThatThrownBy(() -> ActivityJson.parse(null)).hasMessageContaining("json is required");
    }

    private static ActivityResult result(ActivityResult.Outcome outcome, ActivityResult.SubjectKind kind,
                                         Map<String, String> detail) {
        return new ActivityResult(ActivityResult.VERSION, "other.game", "try-1", "sunroot", kind, outcome,
                "reedling", detail);
    }

    /** Replaces one field. {@code raw} is JSON text, quotes included when the value is a string. */
    private static String field(String key, String raw) {
        return envelope(Map.of(key, raw), null);
    }

    /** Appends one extra field to an otherwise valid envelope. */
    private static String extra(String rawField) {
        return envelope(Map.of(), rawField);
    }

    private static String envelope(Map<String, String> overrides, String extra) {
        Map<String, String> fields = new LinkedHashMap<>();
        fields.put("version", "\"activity-result/v1\"");
        fields.put("activityId", "\"other.game\"");
        fields.put("attemptId", "\"try-1\"");
        fields.put("subjectId", "\"sunroot\"");
        fields.put("subjectKind", "\"PLANT\"");
        fields.put("outcome", "\"LEARNED\"");
        fields.put("learned", "\"reedling\"");
        fields.putAll(overrides);
        StringBuilder b = new StringBuilder("{");
        boolean first = true;
        for (Map.Entry<String, String> entry : fields.entrySet()) {
            if (!first) {
                b.append(',');
            }
            first = false;
            b.append('"').append(entry.getKey()).append('"').append(':').append(entry.getValue());
        }
        if (extra != null) {
            b.append(',').append(extra);
        }
        b.append('}');
        return b.toString();
    }

    private static String read(String name) throws IOException {
        Path path = CONTRACT.resolve(name);
        assertThat(Files.isRegularFile(path)).as("missing %s from %s", path, Path.of("").toAbsolutePath()).isTrue();
        return Files.readString(path, StandardCharsets.UTF_8);
    }
}
