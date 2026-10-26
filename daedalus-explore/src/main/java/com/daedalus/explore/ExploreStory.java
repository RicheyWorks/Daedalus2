// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.engine.MazeGrid;

import java.util.List;

/**
 * Handshake for ai-dungeon-master: named locations plus the live pose.
 * No Jackson — the explore module stays Spring-free.
 */
public final class ExploreStory {

    private ExploreStory() {
    }

    public static String export(ExploreWorld world) {
        if (world == null) {
            return "{}";
        }
        return export(world.generatorId(), world.seed(), world.grid(),
                world.markers(), world.body(), world.session());
    }

    public static String export(String generatorId, long seed, MazeGrid grid,
                                List<ExploreMarker> markers, ExploreBody body,
                                ExploreSession session) {
        StringBuilder out = new StringBuilder();
        out.append('{');
        field(out, "generator", generatorId == null ? "dungeon" : generatorId);
        out.append(',');
        out.append("\"seed\":").append(seed);
        if (grid != null) {
            out.append(",\"rows\":").append(grid.rows());
            out.append(",\"cols\":").append(grid.cols());
        }
        out.append(",\"pose\":");
        pose(out, body);
        out.append(",\"locations\":[");
        if (markers != null) {
            for (int i = 0; i < markers.size(); i++) {
                if (i > 0) {
                    out.append(',');
                }
                location(out, markers.get(i));
            }
        }
        out.append("],\"walks\":[");
        if (session != null) {
            List<ExploreSession.Step> steps = session.steps();
            for (int i = 0; i < steps.size(); i++) {
                if (i > 0) {
                    out.append(',');
                }
                ExploreSession.Step step = steps.get(i);
                out.append("{\"from\":");
                point(out, step.from());
                out.append(",\"to\":");
                point(out, step.to());
                out.append('}');
            }
        }
        out.append("]}");
        return out.toString();
    }

    private static void pose(StringBuilder out, ExploreBody body) {
        if (body == null) {
            out.append("null");
            return;
        }
        out.append("{\"row\":").append(body.cell().row());
        out.append(",\"col\":").append(body.cell().col());
        out.append(",\"x\":").append(body.x());
        out.append(",\"z\":").append(body.z());
        out.append(",\"yaw\":").append(body.yaw());
        out.append('}');
    }

    private static void location(StringBuilder out, ExploreMarker marker) {
        out.append('{');
        field(out, "name", marker.name());
        out.append(',');
        field(out, "kind", marker.kind());
        out.append(",\"depth\":").append(marker.depth());
        out.append(",\"row\":").append(marker.cell().row());
        out.append(",\"col\":").append(marker.cell().col());
        out.append('}');
    }

    private static void point(StringBuilder out, com.daedalus.model.Point p) {
        out.append("{\"row\":").append(p.row()).append(",\"col\":").append(p.col()).append('}');
    }

    private static void field(StringBuilder out, String key, String value) {
        out.append('"').append(key).append("\":\"").append(escape(value)).append('"');
    }

    static String escape(String raw) {
        if (raw == null) {
            return "";
        }
        StringBuilder out = new StringBuilder(raw.length());
        for (int i = 0; i < raw.length(); i++) {
            char c = raw.charAt(i);
            if (c == '"' || c == '\\') {
                out.append('\\');
            }
            if (c == '\n') {
                out.append("\\n");
            } else if (c == '\r') {
                out.append("\\r");
            } else {
                out.append(c);
            }
        }
        return out.toString();
    }
}
