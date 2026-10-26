# SPDX-License-Identifier: MIT
"""Shared GLB container admission around the existing importer's pure summary.

This checks framing and strict JSON only; it neither rewrites glTF content nor
evaluates accessors, materials, transforms, external resources or native import.
"""

import struct

JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942


class PayloadError(ValueError):
    """A named GLB member cannot safely pass offline payload admission."""


def validate_glb(data, member, summary, strict_loads):
    """Validate one complete bounded payload using the existing summary callback.

    The caller bounds expanded archive bytes before reading. Unknown extension
    chunks remain opaque, with their framing checked. GLB's JSON and optional
    BIN chunks retain the ordering/cardinality required by the container spec:
    https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#glb-file-format-specification
    """
    try:
        if len(data) < 20:
            raise PayloadError("is too short to be glTF")
        magic, version, length = struct.unpack_from("<III", data, 0)
        if magic != 0x46546C67 or version != 2:
            raise PayloadError("is not glTF 2.0 binary")
        if length != len(data):
            raise PayloadError("declared length does not match payload bytes")
        if length % 4:
            raise PayloadError("container length is not 4-byte aligned")
        offset = 12
        chunk_index = 0
        gltf = None
        while offset < length:
            if length - offset < 8:
                raise PayloadError("truncated chunk header")
            chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
            start = offset + 8
            end = start + chunk_length
            if chunk_length % 4 or end > length:
                kind = "JSON chunk length" if chunk_index == 0 else "chunk length"
                raise PayloadError(kind + " is invalid or unaligned")
            if chunk_index == 0 and chunk_type != JSON_CHUNK:
                raise PayloadError("first chunk must be JSON")
            if chunk_type == JSON_CHUNK:
                if chunk_index != 0:
                    raise PayloadError("duplicate JSON chunk")
                gltf = strict_loads(data[start:end].decode("utf-8"))
                if not isinstance(gltf, dict):
                    raise PayloadError("glTF JSON must be an object")
                if not isinstance(gltf.get("nodes", []), list):
                    raise PayloadError("glTF nodes must be an array")
            elif chunk_type == BIN_CHUNK and chunk_index != 1:
                raise PayloadError("BIN must occur at most once as the second chunk")
            offset = end
            chunk_index += 1
        checked = summary(data)
        if checked != gltf:
            raise PayloadError("existing summary and strict glTF JSON disagree")
        return gltf
    except Exception as error:
        # Callback failures include the existing reader's PackageError; retain
        # the actual cause while exposing a stable named payload boundary.
        raise PayloadError(member + ": " + str(error)) from error
