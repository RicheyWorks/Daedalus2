// SPDX-License-Identifier: MIT

package com.daedalus.world.export;

import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * Writes meshed chunks as one binary glTF 2.0 file (ADR-032): a node per chunk named
 * {@code chunk_<x>_<y>_<z>}, each with up to two primitives (the opaque part with material
 * {@code daedalus_opaque}, the translucent part with {@code daedalus_translucent}, alphaMode BLEND),
 * POSITION / NORMAL / COLOR_0 float attributes and uint32 indices. Y up, right-handed, one cube = one
 * metre: glTF's own conventions, so Blender, Unreal, Godot, Unity and three.js all read it without a
 * transform. No extensions; Khronos' validator passes it with no errors.
 */
public final class Glb {

    private Glb() {
    }

    public static byte[] write(List<WorldMesher.ChunkMesh> chunks, String generator) {
        ByteArrayOutputStream bin = new ByteArrayOutputStream();
        List<String> bufferViews = new ArrayList<>();
        List<String> accessors = new ArrayList<>();
        List<String> meshes = new ArrayList<>();
        List<String> nodes = new ArrayList<>();
        for (WorldMesher.ChunkMesh cm : chunks) {
            List<String> prims = new ArrayList<>();
            if (!cm.opaque().isEmpty()) {
                prims.add(primitive(cm.opaque(), 0, bin, bufferViews, accessors));
            }
            if (!cm.translucent().isEmpty()) {
                prims.add(primitive(cm.translucent(), 1, bin, bufferViews, accessors));
            }
            String name = "chunk_" + cm.at().x() + "_" + cm.at().y() + "_" + cm.at().z();
            meshes.add("{\"name\":\"" + name + "\",\"primitives\":[" + String.join(",", prims) + "]}");
            nodes.add("{\"name\":\"" + name + "\",\"mesh\":" + (meshes.size() - 1) + "}");
        }
        StringBuilder nodeIdx = new StringBuilder();
        for (int i = 0; i < nodes.size(); i++) {
            nodeIdx.append(i == 0 ? "" : ",").append(i);
        }
        int binLength = bin.size();
        String json = "{\"asset\":{\"version\":\"2.0\",\"generator\":\"" + escape(generator) + "\"},"
                + "\"scene\":0,\"scenes\":[{\"name\":\"world\",\"nodes\":[" + nodeIdx + "]}],"
                + "\"nodes\":[" + String.join(",", nodes) + "],"
                + "\"meshes\":[" + String.join(",", meshes) + "],"
                + "\"materials\":["
                + "{\"name\":\"daedalus_opaque\",\"pbrMetallicRoughness\":{\"baseColorFactor\":[1,1,1,1],"
                + "\"metallicFactor\":0,\"roughnessFactor\":0.9}},"
                + "{\"name\":\"daedalus_translucent\",\"alphaMode\":\"BLEND\",\"doubleSided\":true,"
                + "\"pbrMetallicRoughness\":{\"baseColorFactor\":[1,1,1,0.62],\"metallicFactor\":0,\"roughnessFactor\":0.2}}],"
                + "\"accessors\":[" + String.join(",", accessors) + "],"
                + "\"bufferViews\":[" + String.join(",", bufferViews) + "],"
                + "\"buffers\":[{\"byteLength\":" + binLength + "}]}";
        byte[] jsonBytes = pad(json.getBytes(StandardCharsets.UTF_8), (byte) ' ');
        byte[] binBytes = pad(bin.toByteArray(), (byte) 0);
        int total = 12 + 8 + jsonBytes.length + 8 + binBytes.length;
        ByteBuffer out = ByteBuffer.allocate(total).order(ByteOrder.LITTLE_ENDIAN);
        out.putInt(0x46546C67).putInt(2).putInt(total);
        out.putInt(jsonBytes.length).putInt(0x4E4F534A).put(jsonBytes);
        out.putInt(binBytes.length).putInt(0x004E4942).put(binBytes);
        return out.array();
    }

    private static String primitive(WorldMesher.Part p, int material, ByteArrayOutputStream bin,
                                    List<String> views, List<String> accessors) {
        int count = p.vertexCount();
        int pos = floatAccessor(p.positions, count, bin, views, accessors, p.min, p.max);
        int nor = floatAccessor(p.normals, count, bin, views, accessors, null, null);
        int col = floatAccessor(p.colors, count, bin, views, accessors, null, null);
        int offset = bin.size();
        ByteBuffer b = ByteBuffer.allocate(p.indices.size() * 4).order(ByteOrder.LITTLE_ENDIAN);
        for (int i = 0; i < p.indices.size(); i++) {
            b.putInt(p.indices.get(i));
        }
        bin.writeBytes(b.array());
        views.add("{\"buffer\":0,\"byteOffset\":" + offset + ",\"byteLength\":" + b.capacity() + ",\"target\":34963}");
        accessors.add("{\"bufferView\":" + (views.size() - 1) + ",\"componentType\":5125,\"count\":"
                + p.indices.size() + ",\"type\":\"SCALAR\"}");
        int idx = accessors.size() - 1;
        return "{\"attributes\":{\"POSITION\":" + pos + ",\"NORMAL\":" + nor + ",\"COLOR_0\":" + col + "},"
                + "\"indices\":" + idx + ",\"material\":" + material + ",\"mode\":4}";
    }

    private static int floatAccessor(WorldMesher.FloatList data, int count, ByteArrayOutputStream bin,
                                     List<String> views, List<String> accessors, float[] min, float[] max) {
        int offset = bin.size();
        ByteBuffer b = ByteBuffer.allocate(count * 12).order(ByteOrder.LITTLE_ENDIAN);
        for (int i = 0; i < count * 3; i++) {
            b.putFloat(data.get(i));
        }
        bin.writeBytes(b.array());
        views.add("{\"buffer\":0,\"byteOffset\":" + offset + ",\"byteLength\":" + b.capacity()
                + ",\"byteStride\":12,\"target\":34962}");
        String bounds = min == null ? "" : ",\"min\":[" + f(min[0]) + "," + f(min[1]) + "," + f(min[2]) + "],\"max\":["
                + f(max[0]) + "," + f(max[1]) + "," + f(max[2]) + "]";
        accessors.add("{\"bufferView\":" + (views.size() - 1) + ",\"componentType\":5126,\"count\":" + count
                + ",\"type\":\"VEC3\"" + bounds + "}");
        return accessors.size() - 1;
    }

    private static String f(float v) {
        return v == Math.rint(v) ? Integer.toString((int) v) : Float.toString(v);
    }

    private static byte[] pad(byte[] b, byte with) {
        int n = (b.length + 3) & ~3;
        if (n == b.length) {
            return b;
        }
        byte[] out = java.util.Arrays.copyOf(b, n);
        java.util.Arrays.fill(out, b.length, n, with);
        return out;
    }

    private static String escape(String s) {
        return s.replace("\\", "\\\\").replace("\"", "\\\"");
    }
}
